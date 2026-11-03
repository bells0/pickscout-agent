# 导出成本与定价 Skill（v1.0 未定稿）

用户问题：把已维护的成本Skill交给其他工作区使用，不要求复制整个PickScout仓库、私人资料或运行绑定。

导出器每次读取仓库最新的指定源文件，生成自包含的`amazon-cost-pricing/`及`amazon-cost-pricing.zip`。根`skills/amazon-cost-pricing/`和共用方法仍是唯一维护源；生成包及auto-amazon备份只是可使用的版本快照，修订回到PickScout，再重新导出。

## 导出

从仓库运行，明确指定本地输出目录与本次来源commit/ref：

```sh
python3 scripts/export_cost_pricing.py \
  --output-dir artifacts/cost-pricing/delivery/skill-package \
  --source-ref <commit-or-ref>
```

`--source-repo`默认记录公开源仓`https://github.com/bells0/pickscout-agent`，需要时可显式覆盖。来源ref由调用者提供；导出器不访问Git、网络或其他项目。已有同名包/ZIP时拒绝覆盖，另选新输出目录，避免把旧的本地输入混进分享包。

输出目录由调用者选择，不自动安装到用户级Skill目录，不修改配置或源文件。

## 白名单及路径映射

| 维护源 | 包内位置 |
| --- | --- |
| `skills/amazon-cost-pricing/SKILL.md` | `SKILL.md` |
| `skills/amazon-cost-pricing/agents/openai.yaml` | `agents/openai.yaml` |
| `docs/cost-pricing-methodology-v1.0.md` | `references/cost-pricing-methodology-v1.0.md` |
| `docs/decisions/0018-cost-pricing-capability.md` | `references/decisions/0018-cost-pricing-capability.md` |
| `scripts/cost_pricing.py` | `scripts/cost_pricing.py` |
| `scripts/unit_economics.py` | `scripts/unit_economics.py` |
| `templates/cost-pricing-input.json` | `assets/cost-pricing-input.json` |
| `LICENSE` | `LICENSE`（原内容保留） |

仅这8个源文件参与导出，另生成短`README.md`和`SOURCE.json`。本地资源链接按包内位置调整；引用白名单外的本地文件会明确报错，而非自动把目录拷进去。结果路径示例转为调用者本地`outputs/`，不带任何实际任务资料。方法中的仓库位置说明依照本表解释，命令示例以包根为工作目录。

导出前检查包内相对链接及明显的本机/私人绑定引用；这不能代替维护者对源文档进行公开内容审查。真实报价、用户资料、账户数据、`artifacts/`或`data/`下的文件及团队绑定均不在源清单中。

## 独立使用及报告

将整个目录复制走，或把ZIP解压到一个干净目录。进入其中的`amazon-cost-pricing/`后：

```sh
python3 scripts/cost_pricing.py assets/cost-pricing-input.json
```

也可从任意当前目录用实际路径指向脚本和输入。运行只需要Python 3标准库，`unit_economics.py`随包提供；无需原仓库、其他repo或Data插件。示例为合成数据，不是现实报价或Amazon费率。

Agent先读`SKILL.md`及包内方法。没有Data或其他报告插件时，仍能交付完整Markdown或简单HTML：结论、逐项费用/来源/算式、保本、市场候选收益、20%/30%参考价和关键未知。真实输入与结果保存到调用者指定的本地目录，不写入共享快照。

## 验证范围

`tests/test_cost_pricing_export.py`从真实维护源导出并解包到临时干净目录，清除额外模块搜索路径，从无关当前目录真实运行合成计算器，核对结余、保本、目标金额/利润率及未知所得税；同时检查包内文件清单、链接、LICENSE和现有输出不被覆盖。可运行：

```sh
python3 -m unittest discover -s tests -p 'test_cost_pricing_export.py' -v
```

这验证可移植计算与包内容边界，不验证现实商品、市场接受价或当前费率。
