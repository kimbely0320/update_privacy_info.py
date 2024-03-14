# Project API and Dependency Scanner

## English Version

### Description
This script scans a specified project directory for API usage and dependencies, updates or creates a `PrivacyInfo.xcprivacy` file, and generates a text report of the findings.

### Apple Resource
- https://developer.apple.com/documentation/bundleresources/privacy_manifest_files/
- https://developer.apple.com/support/third-party-SDK-requirements/

### Usage
1. **Prerequisites:** Ensure Python 3 is installed on your system.
2. **Running the script:**
   - Open a terminal.
   - Navigate to the script's directory.
   - Run the script using the command:
     ```
     python3 update_privacy_info.py <path-to-your-project-directory>
     ```
3. **Follow the prompts** to choose whether to search for dependencies and whether to exclude any directories.

### Input Prompts
- "Do you want to search for dependencies? (y/n): " - Answer 'y' to search for dependencies or 'n' to skip this step.
- "Do you want to exclude certain directories? (y/n): " - Answer 'y' if you want to exclude directories from the scan.
  - If you chose 'y', you will be prompted: "Please enter directories to exclude (separated by space): ", where you can specify the directories to exclude.

## 中文版本

### 描述
此腳本掃描指定的項目目錄，是否有使用Apple 列出需要註記API和列出套件，更新或創建`PrivacyInfo.xcprivacy`文件，並生成搜索結果的文本報告。

### Apple Resource
- https://developer.apple.com/documentation/bundleresources/privacy_manifest_files/
- https://developer.apple.com/support/third-party-SDK-requirements/

### 使用方法
1. **前提條件：**確保系統上安裝了Python 3。
2. **運行腳本：**
   - 打開終端。
   - 導航至腳本所在目錄。
   - 使用以下命令運行腳本：
     ```
     python3 update_privacy_info.py <項目目錄路徑>
     ```
3. **按提示操作**選擇是否搜索依賴項以及是否排除任何目錄。

### 輸入提示
- "您是否要搜索套件？(y/n): " - 回答'y'開始搜索套件，或者'n'跳過此步驟。
- "您是否要排除某些目錄？(y/n): " - 如果您想從掃描中排除目錄，請回答'y'。
  - 如果您選擇了'y'，將提示："請輸入要排除的目錄（用空格分隔）: "，在此處指定要排除的目錄。
