# 嵌入式框架命名规则与缩写表

[返回框架总规则](../embedded-framework-rules.md)。本细则维护名称形式和缩写词表；数据归属、G_/S_的详细范围见[标识符与变量规则](embedded-data-rules.md)。

日期：2026-10-27。状态：持续打磨；含用户新增的Pascal与下划线组合、Vol/Buf/Dat指定缩写。

## 命名形式

| 对象 | 命名形式 | 边界 |
| --- | --- | --- |
| 自有分层函数 | `APP_模块_动作[对象]`、`FML_模块_动作[对象]`、`HDL_模块_动作[对象]` | 模块和功能中的语义词首字母大写；固定层前缀大写 |
| Task入口 | 沿用既定`Task_功能`及任务契约 | 不为形式统一盲目改名；新增入口与实际任务体系保持一致 |
| 函数参数 | Pascal与下划线结合，例如`Input_Vol`、`Dat_Buf`、`Timeout_Ms` | 各语义片段首字母大写，以`_`分隔；声明与定义一致，不加G_/S_ |
| 结构体标签、typedef类型名和成员 | Pascal与下划线结合，例如`Sample_Dat`、`Input_Vol`、`Ready_Flg` | 位域成员同样执行；SDK/固定外部契约按原名 |
| 结构体对象 | 语义名称用Pascal与下划线结合 | 必要存储前缀另行保留，例如`S_Sample_Dat`、`G_Sample_Dat` |
| 普通自动局部变量 | 大驼峰 | 参数及结构体对象执行上面的专项形式；声明位置见函数规则 |
| 必要跨文件全局对象 | `G_`加大驼峰 | 唯一.c定义，不代表允许任意模块修改 |
| 文件静态、函数静态变量 | `S_`加大驼峰 | static函数不加变量前缀；类型、结构成员不套G_/S_ |
| SDK、启动、中断、固定回调 | 保留平台及外部契约名称 | 不据此要求供应商符号符合自有命名形式 |

名称优先清楚表达含义，可使用完整英文词或已确认/通用缩写，禁止汉语拼音。同一含义在同一套自有命名中保持一致。常规缩写优先3–5个字母，按每个语义词理解；完整词及组合名称可以超过5字母，例如`GetSta`。用户指定缩写和下表例外优先，不强行补齐或截断。

## 已确认缩写

| 英文 | 统一缩写 | 说明 |
| --- | --- | --- |
| State | Sta | 用户明确举例，后续统一使用 |
| Project | Pj | 用户明确指定，作为2字母例外保留 |
| Module | Mod | 用户明确指定，作为模块用词的统一缩写 |
| Voltage | Vol | 2026-10-27用户指定，自有标识符中统一使用 |
| Buffer | Buf | 2026-10-27用户指定，自有标识符中统一使用 |
| Data | Dat | 2026-10-27用户指定，优先于历史参考表中的可选形式 |
| Charge | Chg | 2026-10-27用户允许采用，新增充电模块名称优先使用 |
| Target | Tag | 2026-10-27用户允许采用，新增目标参数名称优先使用，如Tag_Vol |

参数及结构体相关名称采用`Pascal_Underscore`：组合真实语义片段，每段首字母大写，用单个下划线连接，不以全小写snake_case或无下划线的多词PascalCase代替。例如`Input_Vol`、`Dat_Buf`、`Sample_Count`、`struct Mod_Flags`及成员`Fault_Flg`。真实位号或通道号允许数字片段，如`Bit_0`、`Byte_1`；不为凑格式增加无意义数字或片段。

指定缩写优先于一般“允许完整词”原则：新增及实质修改的自有标识符使用Vol/Buf/Dat，不继续写Voltage/Buffer/Data；标准类型、SDK、外部ABI、协议字段文本和归档历史按原契约保留。实际接口改名同步声明、定义和全部调用，不对协议或存储文本做全局替换。

`GetSta`、`SetSta` 是功能组合形式的示例，不代表当前工程已经完成对应API更名。

## 用户提供的英文缩写参考表

以下内容由用户于2026-10-23提供，名称片段统一转为首字母大写。它们是可选参考；含斜线的候选在实际模块中选定一个后保持一致，不表示允许同一含义随意混写。

### A–B

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Adm | Administrator | 管理员 |
| Addr | Address | 地址 |
| App | Application | 应用程序 |
| Arr | Array | 数组 |
| Avg | Average | 平均数 |
| Async | Asynchronization | 异步 |
| Bmp | Bitmap | 位图 |
| Buf | Buffer | 缓冲区 |

### C–D

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Calc | Calculate | 计算 |
| Cdr | Calendar | 日历 |
| Chk | CheckBox | 复选框 |
| Clr | Color | 颜色 |
| Cnt / Cntr | Container | 容器 |
| Cmd | Command | 命令 |
| Cmb | ComboBox | 下拉框 |
| Code | Code | 代码 |
| Ctrl | Control | 控制 |
| Cur | Current | 当前 |
| Dat | Data | 数据；2026-10-27指定只用Dat |
| Del | Delete | 删除 |
| Dest / Dst | Destination | 目的地 |
| Dev | Device | 设备 |
| Diff | Different | 不同的 |
| Dir | Directory | 目录 |
| Disp | Display | 显示 |
| Doc | Document | 文档 |

### E–F

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Dyna | Dynamic | 动态的 |
| Err | Error | 错误 |
| Exec | Execute | 执行 |
| Flg | Flag | 标志 |
| Func | Function | 函数 |
| Frm | Frame | 框架 |

### G–H

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Grp | Group | 组 |
| Hsb | Horizontal Scroll Bar | 水平滚动条 |
| Http | HyperText Transfer Protocol | 超文本传输协议 |

### I–J

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Img | Image | 图像 |
| Info | Information | 信息 |
| Init | Initialize / Initialization | 初始化 |
| Int | Integer | 整数 |
| Io | Input / Output | 输入/输出 |

### K–L

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Key | Key | 键 |
| Lbl | Label | 标签 |
| Lib | Library | 库 |
| Log | Log | 日志 |
| Lst | List | 列表 |

### M–N

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Max | Maximum | 最大值 |
| Min | Minimum | 最小值 |
| Msg | Message | 消息 |
| Mod | Module | 模块 |
| Num | Number | 数字 |

### O–P

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Obj | Object | 对象 |
| Off | Offset | 偏移量 |
| Opr | Operation | 操作 |
| Opt | Option | 选项 |
| Page | Page | 页面 |
| Param | Parameter | 参数 |
| Pass | Password | 密码 |
| Prg | ProgressBar | 进度条 |
| Ptr | Pointer | 指针 |

### Q–R

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Que | Queue | 队列 |
| Rand | Random | 随机 |
| Rec | Record | 记录 |
| Req | Request | 请求 |
| Res | Resource | 资源 |
| Rgb | Red Green Blue | 红绿蓝（颜色模式） |
| Rngsld | Range Slider | 滑块 |

### S–T

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Scr | Screen | 屏幕 |
| Sec | Second | 秒 |
| Set | Set | 集合 |
| Sld | Slider | 滑动器 |
| Sort | Sort | 排序 |
| Spn | SpinBox | 旋转框 |
| Sql | Structured Query Language | 结构化查询语言 |
| Stat | Status | 状态 |
| Str | String | 字符串 |
| Sys | System | 系统 |
| Tbl | Table | 表格 |
| Temp | Temporary | 临时 |
| Test | Test | 测试 |
| Txt | Text | 文本 |
| Tls | Transport Layer Security | 传输层安全性协议 |

### U–V

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Ui | User Interface | 用户界面 |
| Url | Uniform Resource Locator | 统一资源定位符 |
| Usr | User | 用户 |
| Vsb | Vertical Scroll Bar | 垂直滚动条 |
| Ver | Version | 版本 |
| View | View | 视图 |

### W–Z

| 名称片段 | 英文 | 中文 |
| --- | --- | --- |
| Win | Window | 窗口 |
| Xml | Extensible Markup Language | 可扩展标记语言 |
| Zoom | Zoom | 缩放 |

## 参考词的语义和长度边界

- `State → Sta`、`Status → Stat` 分别记录；不同模块若含义有区别，不因中文都叫“状态”就自动合并。
- `Cur` 在本表表示“当前”，不自动解释为物理电流；电流名称结合模块和单位另行明确，避免当前值与电流值混淆。
- `Cnt / Cntr` 在用户参考表中表示Container；既有代码的计数/计数器也可能含Cnt，迁移时按真实语义核对，不能批量当作容器。
- `Chk` 在本表表示CheckBox，`Clr`表示Color，`Temp`表示Temporary，`Res`表示Resource；不能仅凭片段将检查、清零、温度或响应等其他含义替换进去。
- `Set` 在本表表示集合，现有函数中也可作“设置”动作；通过完整接口名区分，不改变实际行为。
- `Io`、`Ui`和已确认的`Pj`为2字母，`Rngsld`为6字母，均按用户参考保留；3–5字母是常用长度，不是强制补齐或截断规则。
- 参考表使用`App`、`Http`、`Io`、`Ui`、`Rgb`等名称片段；固定层前缀仍为`APP`/`FML`/`HDL`，SDK符号、协议文本及线格式不据此改变大小写。
- `Int`是自有名称中的片段，不能据此改写C语言关键字`int`。

## 与其他规则的关系

- 参数及结构体类型/成员/对象执行Pascal与下划线组合，普通局部变量继续大驼峰；静态变量保留S_前缀，声明集中在函数开始。宏命名的完整形式仍需打磨，SDK和固定外部契约保留原名。
- 后续需要为更多词选择缩写时，优先核对本表和模块已有语义；存在多个容易混淆的候选时提交具体名称审核，不凭缩写猜单位或含义。
- 接口更名同步声明、定义、全部实际调用点、测试和说明，不保留两套不一致API。
- 不因改名调整协议字段值、存储布局或增加中断函数跳转。
- 本次只更新规范，尚未把现有 `State` 字段、`Project_*.h` 文件和历史接口批量更名。
