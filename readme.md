# GOBI 地下水年鉴提取项目

本项目用于从地下水监测年鉴 PDF 中提取数据并生成结构化表格。

## Step 1: Initiate venv （首次使用时）

如果是第一次运行项目，需要创建虚拟环境并安装脚本所需的依赖。

在终端中运行 `init_env.sh`：
```bash
chmod +x init_env.sh
source init_env.sh
```

执行成功后将显示：
“虚拟环境创建并已安装依赖。“

### 注意事项：Tesseract 中文语言包配置

本脚本使用 OCR 提取 PDF 中的中文内容，依赖于 Tesseract 的简体中文语言包（`chi_sim.traineddata`）。

项目默认假设语言包位于项目根目录下的：
    GOBI/tessdata/chi_sim.traineddata

请确保：
1. 该文件存在（可通过手动下载或使用 init 脚本自动拉取）
2. `scripts/main_extract.py` 中已自动设置环境变量 `TESSDATA_PREFIX` 指向该目录

如需手动下载语言包，可使用以下命令：

```bash
curl -L -o tessdata/chi_sim.traineddata https://ghproxy.com/https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata
```

或者访问：https://github.com/tesseract-ocr/tessdata 下载所需语言文件。

### 注意事项：有关PaddleOCR

本脚本使用 `PaddleOCR` 提取 PDF 中的中文内容（https://github.com/PaddlePaddle/PaddleOCR/blob/main/README_cn.md）

其优点为可以准确识别文字包括位置，适用于结构复杂的表格。

`PaddleOCR` 需要依赖本地编译器环境（clang），在安装 `PaddleOCR` 之前需要确认安装 `Command Line Tools`:

on Mac Terminal:
```bash
xcode-select --install
```

在 `clang` 安装成功后再进行 `PaddleOCR` 的安装即可。

测试是否成功安装 `PaddleOCR`：

```bash
python -c "from paddleocr import PaddleOCR; print(PaddleOCR())"
```
如果没有出现error message并输出了OCR配置即代表安装成功。

## Step 2: Reactive venv （如果已创建过venv）

如果已经建立过虚拟环境，只需重新启动venv。

```bash
pyenv activate gobi-paddle
```

激活成功后，终端前会出现 `(gobi-paddle)` 前缀，表示当前已在虚拟环境中。

或者可以输入如下命令以在此目录下默认运行 `gobi-paddle` 这个虚拟环境：
```bash
pyenv local gobi-paddle
```

## Step 3: Run Script

在虚拟环境激活状态下，执行脚本：
```bash
python scripts/main_extract.py
```

或根据实际脚本路径替换：
```bash
python PATH/TO/SCRIPT.py
```

## Step 4: Exit venv

运行完毕后退出虚拟环境：
```bash
source deactive
```

退出后终端前缀将消失，返回系统默认 Python 环境。

## 文件结构建议

GOBI/
├── venv/                # 虚拟环境目录（自动生成）
├── scripts/             # Python 脚本
│   └── main_extract.py
├── data/                # 原始 PDF、Excel 数据
├── output/              # 提取结果
├── requirements.txt     # 项目依赖列表
└── init_env.sh          # 初始化虚拟环境脚本
