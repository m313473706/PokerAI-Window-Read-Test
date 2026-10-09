# Poker AI Coach - 完整牌桌状态识别测试版 0.3

这是第三方扑克模拟器的**自动牌桌状态识别测试版**，用于训练/模拟场景。

## 本版新增识别字段

- 我的手牌
- 公共牌
- 底池
- 有效筹码
- 对手人数
- 我的座位/位置
- 当前街道：Preflop / Flop / Turn / River
- 当前对手位置
- 当前行动：Check / Bet / Call / Raise / Fold
- 当前下注金额
- 所有不确定字段支持 `待确认`

## 重要设计

本版本不会为了“看起来完整”而乱猜。

如果 OCR、牌桌布局或视觉证据不足，就输出：

`"status": "待确认"`

例如：

```json
"opponent_action": {
  "value": "待确认",
  "status": "待确认"
}
```

后续版本将通过固定牌桌区域、座位坐标、按钮/庄位标记、筹码变化、行动区域和牌面模板，逐项提高识别准确率。

## 使用

1. 在 GitHub Actions 构建 Windows EXE。
2. 下载 `PokerAI_Full_Table_State_Reader_0_3.exe`。
3. 启动扑克模拟器。
4. 启动测试工具。
5. 选择模拟器窗口。
6. 点击“自动抓取并识别”。
7. 查看右侧 JSON 状态。
8. 查看 `auto_capture/recognition_result.json`。

## 当前限制

Windows `ImageGrab` 需要窗口处于可见状态；如果窗口被完全遮挡或最小化，抓取可能失败。

本版是“完整状态识别测试版”，不是最终识别引擎。尤其是对手人数、位置、行动、下注额、有效筹码，目前在证据不足时会保持“待确认”，不会假装准确。

## 构建

GitHub Actions -> Build Windows Full Table State Reader -> Run workflow。
