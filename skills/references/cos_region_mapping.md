# COS 地域映射表

从 COS URL 中提取地域信息后，需查询本表获取对应的 regionId，再传入 `cos-sign` 命令的 `--region-id` 参数。

## 提取规则

COS URL 格式为 `*.cos.<region>.myqcloud.com`，从中提取 `<region>` 部分（如 `ap-guangzhou`），
然后在下表中查找对应的 regionId。

示例：
- `cos://bucket-123.cos.ap-guangzhou.myqcloud.com/path/file` → 地域 `ap-guangzhou` → regionId `1`
- `https://bucket.cos.ap-beijing.myqcloud.com/path/file` → 地域 `ap-beijing` → regionId `8`

## 完整映射表

| COS 地域名 | regionId | 中文名 |
|---|---|---|
| ap-guangzhou | 1 | 广州 |
| ap-shanghai | 4 | 上海 |
| ap-hongkong | 5 | 香港 |
| na-toronto | 6 | 多伦多 |
| ap-shanghai-fsi | 7 | 上海金融 |
| ap-beijing | 8 | 北京 |
| ap-singapore | 9 | 新加坡 |
| ap-shenzhen-fsi | 11 | 深圳金融 |
| ap-guangzhou-open | 12 | 广州OPEN |
| na-siliconvalley | 15 | 硅谷 |
| ap-chengdu | 16 | 成都 |
| eu-frankfurt | 17 | 法兰克福 |
| ap-seoul | 18 | 首尔 |
| ap-chongqing | 19 | 重庆 |
| ap-mumbai | 21 | 孟买 |
| na-ashburn | 22 | 弗吉尼亚 |
| ap-bangkok | 23 | 曼谷 |
| eu-moscow | 24 | 莫斯科 |
| ap-tokyo | 25 | 日本 |
| ap-jinan-ec | 31 | 济南 |
| ap-hangzhou-ec | 32 | 杭州 |
| ap-nanjing | 33 | 南京 |
| ap-fuzhou-ec | 34 | 福州 |
| ap-wuhan-ec | 35 | 武汉 |
| ap-tianjin | 36 | 天津 |
| ap-shenzhen | 37 | 深圳 |
| ap-taipei | 39 | 台北 |
| me-dubai | 41 | 迪拜 |
| na-losangeles | 42 | 洛杉矶 |
| sl-saopaulo | 43 | 圣保罗 |
| au-sydney | 44 | 悉尼 |
| ap-changsha-ec | 45 | 长沙 |
| ap-beijing-fsi | 46 | 北京金融 |
| ap-others | 47 | 其他 |
| ap-shijiazhuang-ec | 53 | 石家庄 |
| ap-qingyuan | 54 | 清远 |
| ap-hefei-ec | 55 | 合肥 |
| ap-shenyang-ec | 56 | 沈阳 |
| ap-xian-ec | 57 | 西安 |
| ap-xibei-ec | 58 | 西北 |
| ap-zhengzhou-ec | 71 | 郑州 |
| ap-jakarta | 72 | 雅加达 |
| ap-qingyuan-xinan | 73 | 清远西南 |
| sa-saopaulo | 74 | 圣保罗 |
| ap-shenzhen-sycft | 77 | 深圳云 |
| ap-shanghai-adc | 78 | 上海自动驾驶云 |
