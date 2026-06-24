# 测试文件说明

此目录用于存放预览功能测试所需的各类文件样本。

## 测试文件清单

### PDF 文件
- `small.pdf` - 小型 PDF（< 1MB）
- `large.pdf` - 大型 PDF（> 5MB）

### 图片文件
- `image.jpg` - JPEG 图片
- `image.png` - PNG 图片
- `image.gif` - GIF 动图
- `image.webp` - WebP 图片
- `image.svg` - SVG 矢量图

### 视频文件
- `video.mp4` - MP4 视频
- `video.webm` - WebM 视频

### 音频文件
- `audio.mp3` - MP3 音频
- `audio.wav` - WAV 音频

### Office 文件
- `simple.docx` - 简单 Word 文档（纯文本）
- `complex.docx` - 复杂 Word 文档（文本框/绝对定位）
- `simple.xlsx` - 简单 Excel 表格
- `simple.pptx` - 简单 PowerPoint 演示

### 代码/文本文件
- `code.py` - Python 代码
- `code.js` - JavaScript 代码
- `text.md` - Markdown 文档
- `text.json` - JSON 数据

## 创建测试文件

由于测试文件通常较大，建议手动创建或从以下来源获取：

1. **PDF**: 从 https://www.adobe.com/pdf 下载示例
2. **图片**: 使用截图或示例图片
3. **Office**: 创建简单的测试文档

## 使用方式

测试时，设置环境变量指向此目录：

```bash
export UPLOAD_DIR=tests/fixtures/files
```

或在测试代码中：

```python
import os
os.environ['UPLOAD_DIR'] = 'tests/fixtures/files'
```