import argparse
import os
import datetime
import xml.etree.ElementTree as ET
import re

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


# 請求用戶輸入的函數
def user_input(message):
    return input(message)

# 在指定目錄中搜索文件，檢查API使用和套件
def search_files(directory, excluded_dirs):
    found_patterns = {} # 存儲找到的API模式及其位置
    found_deps = set() # 存儲找到的套件

    # 遍歷目錄，忽略排除的目錄
    for root, dirs, files in os.walk(directory, topdown=True):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for file in files:
            # 僅檢查特定擴展名的文件
            if file.endswith(('.swift', '.m', '.h')):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines, start=1):
                        # 對每行進行API模式和套件檢查
                        for category, patterns in api_patterns.items():
                            for pattern in patterns:
                                if re.search(pattern, line):
                                    if category not in found_patterns:
                                        found_patterns[category] = []
                                    found_patterns[category].append((file_path, i))
                        # 檢查依賴
                        for dep in dependencies:
                            if dep in line:
                                found_deps.add(dep)
    return found_patterns, found_deps

# 將搜索結果寫入文本報告
def write_txt_report(output_txt_path, found_patterns, found_deps, search_deps):
    # 創建或覆蓋文本文件，並記錄找到的API模式和套件
    with open(output_txt_path, 'w') as f:
        f.write("Found API Categories:\n")
        for category, occurrences in found_patterns.items():
            f.write(f"- {category}\n")
            file_lines = {}
            for file_path, line in occurrences:
                file_name = os.path.basename(file_path)
                if file_name not in file_lines:
                    file_lines[file_name] = []
                file_lines[file_name].append(str(line))
            for file_name, lines in file_lines.items():
                f.write(f"  {file_name}:{' '.join(lines)}\n")

        if search_deps and found_deps:
            f.write("\nFound Dependencies:\n")
            for dep in found_deps:
                f.write(f"- {dep}\n")

# 更新或創建PrivacyInfo.xcprivacy文件，包含所有必需的API類型
def update_privacy_info(output_path, found_patterns):
    # 嘗試讀取現有的.xcprivacy文件或創建新文件，然後添加新發現的API類型
    try:
        tree = ET.parse(output_path)
        root = tree.getroot()
    except FileNotFoundError:
        root = ET.Element("plist", version="1.0")
        dict_elem = ET.SubElement(root, "dict")
        ET.SubElement(dict_elem, "key").text = "NSPrivacyAccessedAPITypes"
        ET.SubElement(dict_elem, "array")
    except ET.ParseError:  # 文件損壞或為空時，重新創建
        root = ET.Element("plist", version="1.0")
        dict_elem = ET.SubElement(root, "dict")
        ET.SubElement(dict_elem, "key").text = "NSPrivacyAccessedAPITypes"
        ET.SubElement(dict_elem, "array")

    dict_elem = root.find('.//dict')
    api_types_key_found = False
    api_types_array = None
    for child in dict_elem:
        if api_types_key_found:
            if child.tag == 'array':
                api_types_array = child
                break
        elif child.tag == 'key' and child.text == 'NSPrivacyAccessedAPITypes':
            api_types_key_found = True

    if api_types_array is None:
        api_types_array = ET.SubElement(dict_elem, "array")

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

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)

def main():
    parser = argparse.ArgumentParser(description='Scan project directory for API usage and dependencies.')
    parser.add_argument('directory', help='Project directory path')
    args = parser.parse_args()

    # 從用戶獲取輸入，如是否搜索套件，是否排除特定目錄等
    search_deps = user_input("Do you want to search for dependencies 您是否要搜索套件 (y/n): ").lower() == 'y'
    exclude_dirs_choice = user_input("Do you want to exclude certain directories 您是否要排除某些目錄 (y/n): ").lower() == 'y'
    excluded_dirs = []
    if exclude_dirs_choice:
        excluded_dirs = user_input("Please enter directories to exclude (separated by space) 請输入要排除的目錄（用空格分隔）: ").split()

    # 執行文件搜索，然後更新PrivacyInfo.xcprivacy文件和生成報告
    found_patterns, found_deps = search_files(args.directory, excluded_dirs)
    
    # Update PrivacyInfo.xcprivacy and generate the report
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    project_name = os.path.basename(os.path.normpath(args.directory))
    output_path = os.path.join(args.directory, f"PrivacyInfo.xcprivacy")
    output_txt_path = os.path.join(args.directory, f"{project_name}_{current_date}.txt")

    update_privacy_info(output_path, found_patterns)
    write_txt_report(output_txt_path, found_patterns, found_deps, search_deps)

    print(f"PrivacyInfo.xcprivacy file has been updated at {output_path}")
    print(f"Report file has been saved at {output_txt_path}")

if __name__ == "__main__":
    main()