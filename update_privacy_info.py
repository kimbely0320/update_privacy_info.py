import argparse
import os
import datetime
import xml.etree.ElementTree as ET
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# 在全局作用域預編譯正則表達式
compiled_api_patterns = {key: [re.compile(pattern) for pattern in patterns] for key, patterns in api_patterns.items()}
compiled_dep_patterns_swift = {dep: re.compile(r'import\s+' + re.escape(dep)) for dep in dependencies}
compiled_dep_patterns_objc = {dep: re.compile(r'#import\s+["<]' + re.escape(dep) + r'[\./]') for dep in dependencies}


# 請求用戶輸入的函數
def user_input(message):
    return input(message)
    

# 在指定目錄中搜索文件，檢查API使用和套件
# 更新後的搜索文件函數
def process_file(file_path, search_deps):
    found_patterns = {}  # 存儲找到的API模式及其位置
    found_deps = set()  # 存儲找到的套件

    if file_path.endswith(('.swift', '.m', '.h')):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, start=1):
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

    return found_patterns, found_deps

def search_files(directory, excluded_dirs, search_deps):
    files_to_process = []
    for root, dirs, files in os.walk(directory, topdown=True):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for file in files:
            if file.endswith(('.swift', '.m', '.h')):
                file_path = os.path.join(root, file)
                files_to_process.append(file_path)

    # 使用ThreadPoolExecutor並行處理文件
    all_found_patterns = {}
    all_found_deps = set()
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_file, file_path, search_deps) for file_path in files_to_process]
        for future in as_completed(futures):
            found_patterns, found_deps = future.result()
            # 合並找到的模式和套件
            for category, occurrences in found_patterns.items():
                if category not in all_found_patterns:
                    all_found_patterns[category] = occurrences
                else:
                    all_found_patterns[category].extend(occurrences)
            all_found_deps.update(found_deps)

    return all_found_patterns, all_found_deps


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
        excluded_dirs = user_input("Please enter directories to exclude (separated by space) 請輸入要排除的目錄（用空格分隔）: ").split()

    # 執行文件搜索，然後更新PrivacyInfo.xcprivacy文件和生成報告
    found_patterns, found_deps = search_files(args.directory, excluded_dirs, search_deps)
    
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
