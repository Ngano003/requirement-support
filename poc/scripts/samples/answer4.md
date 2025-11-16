# ヌケモレ (ISレイヤー):

REQ-003 (監査ログ) がありますが、FUNC-001 も FUNC-002 も DATA-002 (AuditLog) に MANIPULATES (書き込み) していません。(Requirement に対する Function の実装漏れ)

HW-002 (BLEChip) が定義されていますが、どの Function からも CONTROLS されていません。（ハードウェアの未操作）

# 矛盾 (IS vs SHOULD):

- IS (事実): ACT-002 (User) は FUNC-001 (暗証番号解錠) を USES し、FUNC-001 は HW-001 (Motor) を CONTROLS します。 (パス: User -> Func-001 -> Motor)
- SHOULD (ルール): CONST-S-002 が ACT-001 (管理者) と HW-001 (Motor) に APPLIES_TO されています（暗黙的に User は禁止）。

矛盾: 「User は Motor を（間接的に）制御できる」という事実が、「管理者のみが Motor を制御できる」というルールに違反しています。