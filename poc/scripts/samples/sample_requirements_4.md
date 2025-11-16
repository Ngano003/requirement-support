# スマートロック要件定義書 (SL-REQ-001)

## 1. 概要
本システムは、BLEおよび暗証番号で解錠可能なスマートロックである。

## 2. アクター (Actor)
- ACT-001: 管理者 (Admin)
- ACT-002: 一般ユーザー (User)

## 3. ハードウェア (Hardware)
- HW-001: ドアロックモーター (Motor)
- HW-002: BLEチップ (BLEChip)
- HW-003: キーパッド (Keypad)

## 4. データ (Data)
- DATA-001: 認証キーDB (AuthDB)
- DATA-002: 監査ログ (AuditLog)

## 5. 機能 (Function)
- FUNC-001: 暗証番号解錠
  - HW-003 (Keypad) からの入力を受け取る。
  - DATA-001 (AuthDB) と照合する。
  - 成功時、HW-001 (Motor) を作動させる。
- FUNC-002: 管理者によるキー登録
  - ACT-001 (管理者) のみが実行可能。
  - DATA-001 (AuthDB) にキーを追加する。

## 6. 要件 (Requirement)
- REQ-001: 管理者は、暗証番号を登録・削除できる。(FUNC-002が満たす)
- REQ-002: 一般ユーザーは、暗証番号で解錠できる。(FUNC-001が満たす)
- REQ-003: すべての解錠・施錠操作は、監査ログに記録されること。

## 7. 制約 (Constraint)
- CONST-S-001: 通信はすべてAES-128で暗号化する。 (APPLIES_TO: HW-002, DATA-001)
- CONST-S-002: 管理者のみがモーターを直接制御できる。 (APPLIES_TO: ACT-001, HW-001)
- CONST-P-001: 解錠操作の応答時間は3秒以内とする。 (APPLIES_TO: FUNC-001)