# 工程Log的创建、追加与检索

遵守[LG01–LG06](library/rules/embedded-log-rules.md)，使用[用户字段模板](library/templates/embedded-project-log-template.md)。工程搭建时创建根目录Log，含版本记录.md、提示词记录.md；已有记录不覆盖。资料初始化工具不提前创建固件工程的Log。

可手动使用[版本记录空白文件](../assets/project-log/版本记录.md)与[提示词记录空白文件](../assets/project-log/提示词记录.md)，仅在新工程无同名文件时复制；工具init则只生成两份标题，随后append写入实际完整字段，不创建伪造记录。

每次提问处理前检索相关提示词、模块、引脚、文件或版本记录，再核对当前代码；处理后追加精简提问和实际最终输出。每次完成实际修改后追加版本号、日期、实际文件和变化内容。仅分析、待确认或失败时如实记录，不写成已经实现。版本条目和提示词条目可以互相引用以便检索。

工具仅追加UTF-8记录，保留旧字节、BOM与换行，拒绝覆盖文件冲突/越界路径；一次只由一个维护者写入。它不执行复盘、构建或批准。调用示例：

```text
python -B scripts/project_log.py init --project-root <已进入实施阶段的工程目录>
python -B scripts/project_log.py append-version --project-root <工程目录> --version <实际版本> --files APP/Src/APP_Chg.c --changes <实际修改与验证摘要>
python -B scripts/project_log.py append-prompt --project-root <工程目录> --prompt <本次精简提示词> --result <实际改善输出或待处理项>
```

默认日期/提示词时间来自实际运行系统本地时间（提示词带时区）；补录时显式使用`--date`或`--prompt-time`并在内容说明补录关系。路径中有空格、内容含换行时用所用shell的正常引用或直接调用Python接口，不能拼接不可信shell命令。修改文件路径应相对工程根目录，新增/删除路径也可登记；工具不认证其是否为实际改动。

直接用编辑器追加同样有效；不要用覆盖写入命令清空旧记录。检索可用`rg`针对Log目录的关键词。工程代码摘要、审核证据和C/L三轮表仍单独维护，不能由版本记录替代。
