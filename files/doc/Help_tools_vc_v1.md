# Tools Help
## Virtual Camera Cli V1.0.0

---

命令行读取安卓设备屏幕/摄像头，投射图像至虚拟摄像头（OBS、v4l2loopback、unitycapture）

1. 安装

```bash
pip install "mysc[tools]>=1.5.7"
```

2. 启动指令
```bash
mysc-t-vc
```

3. 执行 ```mysc-t-vc --help``` 查看命令帮助
4. 编写json配置文件，使用 ```mysc-t-vc --config xx.json```执行

例：
```json
｛
  "max_size": 1920,
  "fps": 60,
  "source": "camera",
  "camera_id": 1,
  "camera_ar": "1:1",
  "backend": "obs"
｝
```
更多配置参见 VideoArgs 及 CameraArgs