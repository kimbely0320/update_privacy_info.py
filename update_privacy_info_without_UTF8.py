import argparse
import os
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import time
import chardet

# https://developer.apple.com/documentation/bundleresources/privacy_manifest_files/describing_use_of_required_reason_api
# 根據蘋果官方文檔描述所需的原因 API
api_patterns = {
    "NSPrivacyAccessedAPICategoryFileTimestamp": [
        "creationDate", ".modificationDate", ".fileModificationDate", ".contentModificationDateKey"
    ],
    "NSPrivacyAccessedAPICategorySystemBootTime": [
        "systemUptime", "mach_absolute_time()"
    ],
    "NSPrivacyAccessedAPICategoryDiskSpace": [
        "volumeAvailableCapacityKey", "volumeAvailableCapacityForImportantUsageKey",
        "volumeAvailableCapacityForOpportunisticUsageKey", "volumeTotalCapacityKey", "systemFreeSize", "systemSize"
    ],
    "NSPrivacyAccessedAPICategoryActiveKeyboards": [
        "activeInputModes"
    ],
    "NSPrivacyAccessedAPICategoryUserDefaults": [
        "UserDefaults"
    ]
}

# https://developer.apple.com/support/third-party-SDK-requirements/
# 第三方 SDK 要求
dependencies_info = {
  "Abseil": "https://raw.githubusercontent.com/abseil/abseil-cpp/a41e0168bf2e4f071adc145e0ea8ccec767cd98f/PrivacyInfo.xcprivacy#L4",
  "AFNetworking": "No,Github:https://github.com/AFNetworking/AFNetworking",
  "Alamofire": "https://raw.githubusercontent.com/Alamofire/Alamofire/master/Source/PrivacyInfo.xcprivacy",
  "AppAuth": "https://raw.githubusercontent.com/openid/AppAuth-iOS/master/Sources/AppAuth/Resources/PrivacyInfo.xcprivacy",
  "BoringSSL": "No,Github:https://github.com/google/boringssl",
  "openssl_grpc": "No,Github:https://github.com/openssl/openssl/discussions/23262",
  "Capacitor": "https://raw.githubusercontent.com/ionic-team/capacitor/main/ios/Capacitor/Capacitor/PrivacyInfo.xcprivacy",
  "Charts": "https://raw.githubusercontent.com/danielgindi/Charts/master/Source/Charts/PrivacyInfo.xcprivacy",
  "connectivity_plus": "https://raw.githubusercontent.com/fluttercommunity/plus_plugins/main/packages/connectivity_plus/connectivity_plus/darwin/PrivacyInfo.xcprivacy",
  "Cordova": "https://raw.githubusercontent.com/apache/cordova-ios/master/CordovaLib/PrivacyInfo.xcprivacy",
  "device_info_plus": "https://raw.githubusercontent.com/fluttercommunity/plus_plugins/9e187803d395bf1d8cbe74a0494ef28989451dde/packages/device_info_plus/device_info_plus/ios/PrivacyInfo.xcprivacy",
  "DKImagePickerController": "https://raw.githubusercontent.com/zhangao0086/DKImagePickerController/develop/Sources/DKImagePickerController/Resource/Resources/PrivacyInfo.xcprivacy",
  "DKPhotoGallery": "No,Github:https://github.com/zhangao0086/DKPhotoGallery",
  "FBAEMKit": "https://raw.githubusercontent.com/facebook/facebook-ios-sdk/98c573cc4e997fdc7c58113f84df56eed3a2dfd3/FBAEMKit/FBAEMKit/PrivacyInfo.xcprivacy#L4",
  "FBLPromises": "https://raw.githubusercontent.com/google/promises/540318ecedd63d883069ae7f1ed811a2df00b6ac/Sources/FBLPromises/Resources/PrivacyInfo.xcprivacy#L4",
  "FBSDKCoreKit": "https://raw.githubusercontent.com/facebook/facebook-ios-sdk/98c573cc4e997fdc7c58113f84df56eed3a2dfd3/FBSDKCoreKit/FBSDKCoreKit/PrivacyInfo.xcprivacy#L4",
  "FBSDKCoreKit_Basics": "https://raw.githubusercontent.com/facebook/facebook-ios-sdk/main/FBSDKCoreKit_Basics/FBSDKCoreKit_Basics/PrivacyInfo.xcprivacy",
  "FBSDKLoginKit": "https://raw.githubusercontent.com/facebook/facebook-ios-sdk/98c573cc4e997fdc7c58113f84df56eed3a2dfd3/FBSDKLoginKit/FBSDKLoginKit/PrivacyInfo.xcprivacy#L4",
  "FBSDKShareKit": "https://raw.githubusercontent.com/facebook/facebook-ios-sdk/98c573cc4e997fdc7c58113f84df56eed3a2dfd3/FBSDKShareKit/FBSDKShareKit/PrivacyInfo.xcprivacy#L4",
  "file_picker": "No,Github:https://github.com/miguelpruivo/flutter_file_picker",
  "FirebaseABTesting": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/FirebaseABTesting/Sources/Resources/PrivacyInfo.xcprivacy",
  "FirebaseAuth": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/FirebaseAuth/Sources/Resources/PrivacyInfo.xcprivacy",
  "FirebaseCore": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/FirebaseCore/Sources/Resources/PrivacyInfo.xcprivacy",
  "FirebaseCoreDiagnostics": "No,Github:",
  "FirebaseCoreExtension": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/FirebaseCore/Extension/Resources/PrivacyInfo.xcprivacy",
  "FirebaseCoreInternal": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/FirebaseCore/Internal/Sources/Resources/PrivacyInfo.xcprivacy",
  "FirebaseCrashlytics": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/Crashlytics/Resources/PrivacyInfo.xcprivacy",
  "FirebaseDynamicLinks": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/FirebaseDynamicLinks/Sources/Resources/PrivacyInfo.xcprivacy",
  "FirebaseFirestore": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/Firestore/Swift/Source/Resources/PrivacyInfo.xcprivacy",
  "FirebaseInstallations": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/FirebaseInstallations/Source/Library/Resources/PrivacyInfo.xcprivacy",
  "FirebaseMessaging": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/FirebaseMessaging/Sources/Resources/PrivacyInfo.xcprivacy",
  "FirebaseRemoteConfig": "https://raw.githubusercontent.com/firebase/firebase-ios-sdk/main/FirebaseRemoteConfig/Swift/Resources/PrivacyInfo.xcprivacy",
  "Flutter": "https://raw.githubusercontent.com/flutter/engine/a565cea256c7bafeaa0c26c2f1b0d66a52692d02/shell/platform/darwin/ios/framework/PrivacyInfo.xcprivacy#L9-L12",
  "flutter_inappwebview": "https://raw.githubusercontent.com/flutter/packages/main/packages/webview_flutter/webview_flutter_wkwebview/ios/Resources/PrivacyInfo.xcprivacy",
  "flutter_local_notifications": "https://raw.githubusercontent.com/MaikuB/flutter_local_notifications/master/flutter_local_notifications/ios/Resources/PrivacyInfo.xcprivacy",
  "fluttertoast": "No,GitHub:https://github.com/ponnamkarthik/FlutterToast",
  "FMDB": "https://raw.githubusercontent.com/ccgus/fmdb/master/privacy/PrivacyInfo.xcprivacy",
  "geolocator_apple": "https://raw.githubusercontent.com/Baseflow/flutter-geolocator/main/geolocator_apple/ios/Resources/PrivacyInfo.xcprivacy",
  "GoogleDataTransport": "https://raw.githubusercontent.com/google/GoogleDataTransport/main/GoogleDataTransport/Resources/PrivacyInfo.xcprivacy",
  "GoogleSignIn": "https://raw.githubusercontent.com/google/GoogleSignIn-iOS/main/GoogleSignIn/Sources/Resources/PrivacyInfo.xcprivacy",
  "GoogleToolboxForMac": "https://raw.githubusercontent.com/google/google-toolbox-for-mac/main/Resources/Base/PrivacyInfo.xcprivacy",
  "GoogleUtilities": "https://raw.githubusercontent.com/google/GoogleUtilities/main/GoogleUtilities/Privacy/Resources/PrivacyInfo.xcprivacy",
  "grpcpp": "https://raw.githubusercontent.com/grpc/grpc/master/src/objective-c/PrivacyInfo.xcprivacy",
  "GTMAppAuth": "https://raw.githubusercontent.com/google/GTMAppAuth/master/GTMAppAuth/Sources/Resources/PrivacyInfo.xcprivacy",
  "GTMSessionFetcher": {
    "Core": "https://raw.githubusercontent.com/google/gtm-session-fetcher/main/Sources/Core/Resources/PrivacyInfo.xcprivacy",
    "Full": "https://raw.githubusercontent.com/google/gtm-session-fetcher/main/Sources/Full/Resources/PrivacyInfo.xcprivacy",
    "LoginView": "https://raw.githubusercontent.com/google/gtm-session-fetcher/main/Sources/LogView/Resources/PrivacyInfo.xcprivacy"
  },
  "hermes": "No,GitHub:https://github.com/facebook/hermes",
  "image_picker_ios": "https://raw.githubusercontent.com/flutter/packages/main/packages/image_picker/image_picker_ios/ios/Resources/PrivacyInfo.xcprivacy",
  "IQKeyboardManager": "https://raw.githubusercontent.com/hackiftekhar/IQKeyboardManager/master/IQKeyboardManager/PrivacyInfo.xcprivacy",
  "IQKeyboardManagerSwift": "https://raw.githubusercontent.com/hackiftekhar/IQKeyboardManager/master/IQKeyboardManagerSwift/PrivacyInfo.xcprivacy",
  "Kingfisher": "https://raw.githubusercontent.com/onevcat/Kingfisher/master/Sources/PrivacyInfo.xcprivacy",
  "leveldb": "No,GitHub:https://github.com/google/leveldb",
  "Lottie": "https://raw.githubusercontent.com/airbnb/lottie-ios/master/Sources/PrivacyInfo.xcprivacy",
  "MBProgressHUD": "https://raw.githubusercontent.com/jdg/MBProgressHUD/master/PrivacyInfo.xcprivacy",
  "nanopb": "https://raw.githubusercontent.com/nanopb/nanopb/master/spm_resources/PrivacyInfo.xcprivacy",
  "OneSignal": "https://raw.githubusercontent.com/OneSignal/OneSignal-iOS-SDK/5ff232ea9392f63e87306752025a45eceb18fa5b/iOS_SDK/OneSignalSDK/Source/PrivacyInfo.xcprivacy#L4",
  "OneSignalCore": "No,GitHub: https://github.com/OneSignal/OneSignal-iOS-SDK/tree/5ff232ea9392f63e87306752025a45eceb18fa5b/iOS_SDK/OneSignalSDK/OneSignalCore",
  "OneSignalExtension": "https://raw.githubusercontent.com/OneSignal/OneSignal-iOS-SDK/5ff232ea9392f63e87306752025a45eceb18fa5b/iOS_SDK/OneSignalSDK/OneSignalExtension/PrivacyInfo.xcprivacy#L4",
  "OneSignalOutcomes": "No,GitHub:https://github.com/OneSignal/OneSignal-iOS-SDK/tree/5ff232ea9392f63e87306752025a45eceb18fa5b/iOS_SDK/OneSignalSDK/OneSignalOutcomes",
  "OpenSSL": "No,GitHub:https://github.com/openssl/openssl",
  "OrderedSet": "No,GitHub:https://github.com/Weebly/OrderedSet",
  "package_info": "No,GitHub:https://github.com/flutter/plugins",
  "package_info_plus": "https://raw.githubusercontent.com/fluttercommunity/plus_plugins/main/packages/package_info_plus/package_info_plus/ios/PrivacyInfo.xcprivacy",
  "path_provider": "https://raw.githubusercontent.com/flutter/packages/main/packages/path_provider/path_provider_foundation/darwin/Resources/PrivacyInfo.xcprivacy",
  "path_provider_ios": "https://raw.githubusercontent.com/flutter/packages/main/packages/path_provider/path_provider_foundation/darwin/Resources/PrivacyInfo.xcprivacy",
  "Promises": "https://raw.githubusercontent.com/google/promises/master/Sources/Promises/Resources/PrivacyInfo.xcprivacy",
  "Protobuf": "https://raw.githubusercontent.com/protocolbuffers/protobuf/main/PrivacyInfo.xcprivacy",
  "Reachability": "https://raw.githubusercontent.com/ashleymills/Reachability.swift/master/Sources/PrivacyInfo.xcprivacy",
  "RealmSwift": "https://raw.githubusercontent.com/realm/realm-swift/master/RealmSwift/PrivacyInfo.xcprivacy",
  "RxCocoa": "No,GitHub:https://github.com/ReactiveX/RxSwift/issues/2567",
  "RxRelay": "No,GitHub:https://github.com/ReactiveX/RxSwift/issues/2567",
  "RxSwift": "No,GitHub:https://github.com/ReactiveX/RxSwift/issues/2567",
  "SDWebImage": "https://raw.githubusercontent.com/SDWebImage/SDWebImage/master/WebImage/PrivacyInfo.xcprivacy",
  "share_plus": "https://raw.githubusercontent.com/fluttercommunity/plus_plugins/main/packages/share_plus/share_plus/ios/PrivacyInfo.xcprivacy",
  "shared_preferences_ios": "https://raw.githubusercontent.com/flutter/packages/main/packages/shared_preferences/shared_preferences_foundation/darwin/Resources/PrivacyInfo.xcprivacy",
  "SnapKit": "https://raw.githubusercontent.com/SnapKit/SnapKit/develop/Sources/PrivacyInfo.xcprivacy",
  "sqflite": "https://raw.githubusercontent.com/tekartik/sqflite/master/sqflite/darwin/Resources/PrivacyInfo.xcprivacy",
  "Starscream": "https://raw.githubusercontent.com/daltoniam/Starscream/master/Sources/PrivacyInfo.xcprivacy",
  "SVProgressHUD": "https://raw.githubusercontent.com/SVProgressHUD/SVProgressHUD/master/SVProgressHUD/PrivacyInfo.xcprivacy",
  "SwiftyGif": "https://raw.githubusercontent.com/kirualex/SwiftyGif/master/SwiftyGif/PrivacyInfo.xcprivacy",
  "SwiftyJSON": "https://raw.githubusercontent.com/Nathan-Molby/SwiftyJSON/master/Source/SwiftyJSON/PrivacyInfo.xcprivacy",
  "Toast": "https://raw.githubusercontent.com/scalessec/Toast-Swift/master/Toast/Resources/PrivacyInfo.xcprivacy",
  "UnityFramework": "No,GitHub:",
  "url_launcher": "https://raw.githubusercontent.com/flutter/packages/main/packages/url_launcher/url_launcher_ios/ios/Resources/PrivacyInfo.xcprivacy",
  "url_launcher_ios": "https://raw.githubusercontent.com/flutter/packages/main/packages/url_launcher/url_launcher_ios/ios/Resources/PrivacyInfo.xcprivacy",
  "video_player_avfoundation": "https://raw.githubusercontent.com/flutter/packages/main/packages/video_player/video_player_avfoundation/darwin/Resources/PrivacyInfo.xcprivacy",
  "wakelock": "No,GitHub:https://github.com/creativecreatorormaybenot/wakelock",
  "webview_flutter_wkwebview": "https://raw.githubusercontent.com/flutter/packages/main/packages/webview_flutter/webview_flutter_wkwebview/ios/Resources/PrivacyInfo.xcprivacy",
  "CocoaLumberjack": "https://raw.githubusercontent.com/CocoaLumberjack/CocoaLumberjack/master/Sources/CocoaLumberjack/PrivacyInfo.xcprivacy"
}


compiled_attracking_pattern = re.compile(r'ATTrackingManager.requestTrackingAuthorization')

# 在全局作用域預編譯正則表達式
# Precompile regular expressions for global scope
compiled_api_patterns = {key: [re.compile(pattern) for pattern in patterns] for key, patterns in api_patterns.items()}
compiled_dep_patterns_swift = {dep: re.compile(r'import\s+' + re.escape(dep)) for dep in dependencies_info.keys()}
compiled_dep_patterns_objc = {dep: re.compile(r'#import\s+["<]' + re.escape(dep) + r'[\./]') for dep in dependencies_info.keys()}

# 請求用戶輸入的函數
# Function to request user input
def user_input(message):
    return input(message)
    

def download_file(url, save_path):
    """
    Download a file from a URL and save it to the specified path using urllib.
    從 URL 下載文件並使用 urllib 保存到指定路徑。
    """
    try:
        with urllib.request.urlopen(url) as response, open(save_path, 'wb') as out_file:
            data = response.read()  # a `bytes` object
            out_file.write(data)
        print(f"File downloaded successfully and saved to {save_path}")
    except Exception as e:
        print(f"An error occurred while downloading the file: {e}")


def process_dependency(name, url_info, base_dir="Deps_PrivacyInfos"):
    """
    處理每個套件的下載邏輯。
    Process the download logic for each dependency.
    """
    if "No,GitHub:" in url_info:
        print(f"No download link for {name}, skipping.GitHub: {url_info}")
        return

    target_dir = os.path.join(base_dir, name)
    os.makedirs(target_dir, exist_ok=True)

    if isinstance(url_info, str):  # 單個URL
        download_file(url_info, os.path.join(target_dir, "PrivacyInfo.xcprivacy"))
        print(f"Downloaded PrivacyInfo.xcprivacy for {name}.")
    elif isinstance(url_info, dict):  # URL信息是字典形式
        for key, url in url_info.items():
            sub_dir = os.path.join(target_dir, key)
            os.makedirs(sub_dir, exist_ok=True)
            download_file(url, os.path.join(sub_dir, "PrivacyInfo.xcprivacy"))
            print(f"Downloaded PrivacyInfo.xcprivacy for {name} ({key}).")


def process_file(file_path, is_api_search, search_deps, found_attracking):
    """
    在指定目录中搜索文件，检查API使用和依赖
    Search for files in a specified directory, checking for API usage and dependencies
    """
    found_patterns = {}
    found_deps = set()
    if file_path.endswith(('.swift', '.m', '.h')):
        # Detect the encoding of the file
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            detected_encoding = chardet.detect(raw_data).get('encoding')

        # If the encoding was detected, proceed to read the file
        if detected_encoding:
            try:
                with open(file_path, 'r', encoding=detected_encoding) as f:
                    lines = f.readlines()
                
                # Convert lines to UTF-8
                new_lines = []
                for line in lines:
                    try:
                        # Try encoding with detected encoding and decoding to UTF-8
                        new_line = line.encode(detected_encoding).decode('utf-8')
                        new_lines.append(new_line)
                    except UnicodeDecodeError:
                        # If there's an error, replace problematic characters
                        new_line = line.encode(detected_encoding, errors='replace').decode('utf-8')
                        new_lines.append(new_line)

                lines = new_lines
            except UnicodeDecodeError as e:
                print(f"Error reading {file_path} with detected encoding {detected_encoding}: {e}")
                return found_patterns, found_deps, found_attracking
        else:
            return found_patterns, found_deps, found_attracking

        for i, line in enumerate(lines, start=1):
            if is_api_search:
                for category, patterns in compiled_api_patterns.items():
                    for pattern in patterns:
                        if pattern.search(line):
                            if category not in found_patterns:
                                found_patterns[category] = []
                            found_patterns[category].append((file_path, i))
            if search_deps:
                if file_path.endswith('.swift'):
                    for dep, pattern in compiled_dep_patterns_swift.items():
                        if pattern.search(line):
                            found_deps.add(dep)
                elif file_path.endswith(('.h', '.m')):
                    for dep, pattern in compiled_dep_patterns_objc.items():
                        if pattern.search(line):
                            found_deps.add(dep)
                if compiled_attracking_pattern.search(line):
                    found_attracking = True

    return found_patterns, found_deps, found_attracking



def search_files(directory, excluded_dirs_api, excluded_dirs_deps, search_apis, search_deps):

    """
    Search through the project directory for API usage and dependencies, excluding specified directories.
    在項目目錄中搜索API使用情況和套件關係，排除指定的目錄。
    """

    files_to_process = []
    found_attracking = False
    # 分別處理API搜索和套件搜索
    if search_apis:
        for root, dirs, files in os.walk(directory, topdown=True):
            dirs[:] = [d for d in dirs if d not in excluded_dirs_api]
            for file in files:
                if file.endswith(('.swift', '.m', '.h')):
                    file_path = os.path.join(root, file)
                    files_to_process.append((file_path, True))  # True表示這是API搜索

    if search_deps:
        for root, dirs, files in os.walk(directory, topdown=True):
            dirs[:] = [d for d in dirs if d not in excluded_dirs_deps]
            for file in files:
                if file.endswith(('.swift', '.m', '.h')):
                    file_path = os.path.join(root, file)
                    # 確保在同時進行API和套件搜索時不重覆添加文件
                    if not search_apis or (file_path, True) not in files_to_process:
                        files_to_process.append((file_path, False))  # False表示這是套件搜索

    total_files = len(files_to_process)
    files_processed = 0

    all_found_patterns = {}
    all_found_deps = set()
    search_tracking_auth_found = False

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_file, file_path, search_api, search_deps, found_attracking) for file_path, search_api in files_to_process]
    for future in as_completed(futures):
        files_processed += 1
        found_patterns, found_deps, search_tracking_auth = future.result()
        if search_tracking_auth:
            search_tracking_auth_found = True
        for category, occurrences in found_patterns.items():
            if category not in all_found_patterns:
                all_found_patterns[category] = occurrences
            else:
                all_found_patterns[category].extend(occurrences)
        all_found_deps.update(found_deps)
        # 更新進度
        progress = (files_processed / total_files) * 100
        sys.stdout.write(f"\rProgress: {progress:.2f}% ({files_processed}/{total_files})")
        sys.stdout.flush()

    print("\nDone processing files.")
    return all_found_patterns, all_found_deps, search_tracking_auth_found



# 將搜索結果寫入文本報告
def write_txt_report(output_txt_path, found_patterns, found_deps, search_deps):

    """
    Write the search results to a text report, including found API categories and dependencies.
    將搜索結果寫入文本報告，包括找到的API類別和套件。
    """

    with open(output_txt_path, 'w') as f:
        f.write("Found API Categories:\n")
        for category, occurrences in found_patterns.items():
            f.write(f"- {category}\n")
            for file_path, line in occurrences:
                f.write(f"  {os.path.basename(file_path)}: Line {line}\n")

        if search_deps:
            f.write("\nFound Dependencies:\n")
            for dep in found_deps:
                f.write(f"\n- {dep}")
                if dep in dependencies_info:
                    url_info = dependencies_info[dep]
                    if url_info == "No":
                        f.write(f"\n - No download link available\n")
                    elif isinstance(url_info, str):
                        f.write(f"\n - {url_info}\n")
                    elif isinstance(url_info, dict):
                        for key, url in url_info.items():
                            f.write(f"\n  {key}: {url}\n")
                else:
                    f.write(f"\n - Dependency information not found\n")

def remove_ns_privacy_tracking_element(dict_elem):
    children = list(dict_elem)
    for i, child in enumerate(children):
        # 找到NSPrivacyTracking鍵
        if child.tag == 'key' and child.text == 'NSPrivacyTracking':
            
            if i + 1 < len(children) and children[i + 1].tag in ['true', 'false']:
                dict_elem.remove(children[i])   # 刪除<key>
                dict_elem.remove(children[i + 1]) # 刪除<true/>或<false/>
            break


def update_privacy_info(output_path, found_patterns, found_attracking):

    """
    Update or create a PrivacyInfo.xcprivacy file with all required API types.
    使用所有必需的API類型更新或創建PrivacyInfo.xcprivacy文件。
    """
    try:
        tree = ET.parse(output_path)
        root = tree.getroot()
    except FileNotFoundError:
        root = ET.Element("plist", version="1.0")
        dict_elem = ET.SubElement(root, "dict")
    except ET.ParseError:
        root = ET.Element("plist", version="1.0")
        dict_elem = ET.SubElement(root, "dict")

    dict_elem = root.find('.//dict')

    # Remove existing NSPrivacyTracking if present
    # 如果存在，則移除現有的NSPrivacyTracking。
    #remove_ns_privacy_tracking_element(dict_elem)

    # Ensure the NSPrivacyAccessedAPITypes key and its array are correctly structured
    # 確保NSPrivacyAccessedAPITypes鍵及其數組結構正確。
    if not dict_elem.find("key[@text='NSPrivacyAccessedAPITypes']"):
        ET.SubElement(dict_elem, "key").text = "NSPrivacyAccessedAPITypes"
        api_types_array = ET.SubElement(dict_elem, "array")
    else:
        api_types_array = dict_elem.find(".//array")

    existing_api_types = set()
    for api_type_dict in api_types_array.findall("dict"):
        api_type_string = api_type_dict.find("string").text
        existing_api_types.add(api_type_string)

    for pattern in found_patterns:
        if pattern not in existing_api_types:
            new_dict = ET.SubElement(api_types_array, "dict")
            ET.SubElement(new_dict, "key").text = "NSPrivacyAccessedAPIType"
            ET.SubElement(new_dict, "string").text = pattern
            reasons_key = ET.SubElement(new_dict, "key")
            reasons_key.text = "NSPrivacyAccessedAPITypeReasons"
            reasons_array = ET.SubElement(new_dict, "array")
            reason_string = ET.SubElement(reasons_array, "string")
            reason_string.text = "請在此處插入 " + pattern + " 原因"

    # Re-add NSPrivacyTracking at the end with the correct value
    # 在最後重新添加NSPrivacyTracking，並設置正確的值。
    #ET.SubElement(dict_elem, "key").text = "NSPrivacyTracking"
    #ET.SubElement(dict_elem, 'true' if found_attracking else 'false')

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)


def filter_valid_dependencies(found_deps):
    """
    Filter and return valid dependencies based on `dependencies_info`.
    基於 dependencies_info 篩選並返回有效的套件。
    
    """
    valid_deps = {}
    for dep in found_deps:
        if dep in dependencies_info:
            url_info = dependencies_info[dep]
            # Check if url_info is a string and doesn't start with "No,Github:"
            # 檢查url_info是否不以"No,Github:"開頭。
            if isinstance(url_info, str) and not url_info.startswith("No,Github:"):
                valid_deps[dep] = url_info
            # If url_info is a dictionary, consider it valid
            # 如果url_info是Key，則視其為有效
            elif isinstance(url_info, dict):
                valid_deps[dep] = url_info
            else:
                print(f"Skipping download for {dep} due to lack of direct download URL 由於缺乏直接下載鏈接，跳過對 {dep} 的下載")
        else:
            print(f"No download info available for {dep}, skipping {dep} 沒有下載信息可用，繼續")
    return valid_deps

def process_valid_dependencies(valid_deps, base_dir):
    """
    Process and download each valid dependency.
    處理並下載每個有效的套件。
    """
    for dep, url_info in valid_deps.items():
        print(f"Processing dependency: {dep}")
        process_dependency(dep, url_info, base_dir)

def main():
    parser = argparse.ArgumentParser(description='Scan project directory for API usage and dependencies.')
    parser.add_argument('directory', help='Project directory path')
    args = parser.parse_args()

    # 從用戶獲取輸入，如是否搜索套件，是否排除特定目錄等
    search_apis = user_input("Do you want to search for API usage 是否要搜索API使用情況 (y/n): ").lower() == 'y'
    if search_apis:
        exclude_dirs_api_choice = user_input("Do you want to exclude certain directories for API search 您是否要為API搜索排除某些目錄 (y/n): ").lower() == 'y'
        excluded_dirs_api = []
        if exclude_dirs_api_choice:
            excluded_dirs_api = user_input("Please enter directories to exclude for API search (separated by space) 請為API搜索輸入要排除的目錄（用空格分隔）: ").split()
    
    # 詢問是否搜索套件，並獲取排除目錄信息
    search_deps = user_input("Do you want to search for dependencies 是否要搜索套件是否有在列表中 (y/n): ").lower() == 'y'
    if search_deps:
        exclude_dirs_deps_choice = user_input("Do you want to exclude certain directories for dependencies search 您是否要為套件搜索排除某些目錄 (y/n): ").lower() == 'y'
        excluded_dirs_deps = []
        if exclude_dirs_deps_choice:
            excluded_dirs_deps = user_input("Please enter directories to exclude for dependencies search (separated by space) 請為套件搜索輸入要排除的目錄（用空格分隔）: ").split()

        download_privacy_info = user_input("Do you want to download privacy_info for dependencies 是否要下載套件的 privacy_info (y/n): ").lower() == 'y'

    # Execute file search, then update PrivacyInfo.xcprivacy file and generate report
    found_patterns, found_deps, search_tracking_auth = search_files(args.directory, excluded_dirs_api, excluded_dirs_deps, search_apis, search_deps)
    
    # Update PrivacyInfo.xcprivacy and generate the report
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    project_name = os.path.basename(os.path.normpath(args.directory))
    output_path = os.path.join(args.directory, f"PrivacyInfo.xcprivacy")
    output_txt_path = os.path.join(args.directory, f"{project_name}_{current_date}.txt")

    update_privacy_info(output_path, found_patterns, search_tracking_auth)

    if download_privacy_info:
        # Filter and process valid dependencies
        base_dir = os.path.join(args.directory, "Deps_PrivacyInfos")  # Directory to save downloaded files
        os.makedirs(base_dir, exist_ok=True)  # Ensure the base directory exists
        valid_deps = filter_valid_dependencies(found_deps)
        process_valid_dependencies(valid_deps, base_dir)

    write_txt_report(output_txt_path, found_patterns, found_deps, search_deps)

    print(f"PrivacyInfo.xcprivacy file has been updated at 文件已更新，位於 {output_path}")
    print(f"Report file has been saved at 報告文件已保存至 {output_txt_path}")

    print(f"PrivacyInfo.xcprivacy file has been updated at 文件已更新，位於{output_path}")
    print(f"Report file has been saved at 報告文件已保存至{output_txt_path}")

if __name__ == "__main__":
    main()

