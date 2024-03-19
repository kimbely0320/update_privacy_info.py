import argparse
import os
import datetime
import xml.etree.ElementTree as ET
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import time

# https://developer.apple.com/documentation/bundleresources/privacy_manifest_files/describing_use_of_required_reason_api
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
dependencies = [
    "Abseil", "AFNetworking", "Alamofire", "AppAuth", "BoringSSL", "openssl_grpc",
    "Capacitor", "Charts", "connectivity_plus", "Cordova", "device_info_plus",
    "DKImagePickerController", "DKPhotoGallery", "FBAEMKit", "FBLPromises",
    "FBSDKCoreKit", "FBSDKCoreKit_Basics", "FBSDKLoginKit", "FBSDKShareKit",
    "file_picker", "FirebaseABTesting", "FirebaseAuth", "FirebaseCore",
    "FirebaseCoreDiagnostics", "FirebaseCoreExtension", "FirebaseCoreInternal",
    "FirebaseCrashlytics", "FirebaseDynamicLinks", "FirebaseFirestore",
    "FirebaseInstallations", "FirebaseMessaging", "FirebaseRemoteConfig", "Flutter",
    "flutter_inappwebview", "flutter_local_notifications", "fluttertoast", "FMDB",
    "geolocator_apple", "GoogleDataTransport", "GoogleSignIn", "GoogleToolboxForMac",
    "GoogleUtilities", "grpcpp", "GTMAppAuth", "GTMSessionFetcher", "hermes",
    "image_picker_ios", "IQKeyboardManager", "IQKeyboardManagerSwift", "Kingfisher",
    "leveldb", "Lottie", "MBProgressHUD", "nanopb", "OneSignal", "OneSignalCore",
    "OneSignalExtension", "OneSignalOutcomes", "OpenSSL", "OrderedSet", "package_info",
    "package_info_plus", "path_provider", "path_provider_ios", "Promises", "Protobuf",
    "Reachability", "RealmSwift", "RxCocoa", "RxRelay", "RxSwift", "SDWebImage",
    "share_plus", "shared_preferences_ios", "SnapKit", "sqflite", "Starscream",
    "SVProgressHUD", "SwiftyGif", "SwiftyJSON", "Toast", "UnityFramework", "url_launcher",
    "url_launcher_ios", "video_player_avfoundation", "wakelock", "webview_flutter_wkwebview"
]

compiled_attracking_pattern = re.compile(r'ATTrackingManager.requestTrackingAuthorization')

# 在全局作用域預編譯正則表達式
compiled_api_patterns = {key: [re.compile(pattern) for pattern in patterns] for key, patterns in api_patterns.items()}
compiled_dep_patterns_swift = {dep: re.compile(r'import\s+' + re.escape(dep)) for dep in dependencies}
compiled_dep_patterns_objc = {dep: re.compile(r'#import\s+["<]' + re.escape(dep) + r'[\./]') for dep in dependencies}

# 請求用戶輸入的函數
def user_input(message):
    return input(message)
    
    
# 在指定目錄中搜索文件，檢查API使用和套件
# 更新後的搜索文件函數
def process_file(file_path, is_api_search, search_deps, found_attracking):
    found_patterns = {}
    found_deps = set()
    if file_path.endswith(('.swift', '.m', '.h')):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, start=1):
                if is_api_search:  # Now using the is_api_search flag
                    for category, patterns in compiled_api_patterns.items():
                        for pattern in patterns:
                            if pattern.search(line):
                                if category not in found_patterns:
                                    found_patterns[category] = []
                                found_patterns[category].append((file_path, i))
                if search_deps:  # Dependency search check remains the same
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
    with open(output_txt_path, 'w') as f:
        f.write("Found API Categories:\n")
        for category, occurrences in found_patterns.items():
            f.write(f"- {category}\n")
            file_lines = {}
            for occurrence in occurrences:
                if len(occurrence) == 2:
                    file_path, line = occurrence
                    file_name = os.path.basename(file_path)
                    if file_name not in file_lines:
                        file_lines[file_name] = []
                    file_lines[file_name].append(str(line))
                else:
                    # 如果不匹配，打印一個錯誤或警告
                    print(f"Unexpected occurrence format: {occurrence}")
            for file_name, lines in file_lines.items():
                f.write(f"  {file_name}: {' '.join(lines)}\n")

        if search_deps and found_deps:
            f.write("\nFound Dependencies:\n")
            for dep in found_deps:
                f.write(f"- {dep}\n")

def remove_ns_privacy_tracking_element(dict_elem):
    children = list(dict_elem)
    for i, child in enumerate(children):
        # 找到NSPrivacyTracking鍵
        if child.tag == 'key' and child.text == 'NSPrivacyTracking':
            
            if i + 1 < len(children) and children[i + 1].tag in ['true', 'false']:
                dict_elem.remove(children[i])   # 刪除<key>
                dict_elem.remove(children[i + 1]) # 刪除<true/>或<false/>
            break

# 更新或創建PrivacyInfo.xcprivacy文件，包含所有必需的API類型
def update_privacy_info(output_path, found_patterns, found_attracking):
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
    remove_ns_privacy_tracking_element(dict_elem)

    # Ensure the NSPrivacyAccessedAPITypes key and its array are correctly structured
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
    ET.SubElement(dict_elem, "key").text = "NSPrivacyTracking"
    ET.SubElement(dict_elem, 'true' if found_attracking else 'false')

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)


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

    # 執行文件搜索，然後更新PrivacyInfo.xcprivacy文件和生成報告
    found_patterns, found_deps, search_tracking_auth = search_files(args.directory, excluded_dirs_api, excluded_dirs_deps, search_apis, search_deps)
    
    # Update PrivacyInfo.xcprivacy and generate the report
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    project_name = os.path.basename(os.path.normpath(args.directory))
    output_path = os.path.join(args.directory, f"PrivacyInfo.xcprivacy")
    output_txt_path = os.path.join(args.directory, f"{project_name}_{current_date}.txt")

    update_privacy_info(output_path, found_patterns, search_tracking_auth)
    write_txt_report(output_txt_path, found_patterns, found_deps, search_deps)

    print(f"PrivacyInfo.xcprivacy file has been updated at {output_path}")
    print(f"Report file has been saved at {output_txt_path}")

if __name__ == "__main__":
    main()
