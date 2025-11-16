# 搬送ボット要件定義書 (WB-REQ-002)

## 1. 概要
本システムは、倉庫内の棚(A)から梱包エリア(B)へ自動で物品を搬送するAGV(無人搬送車)である。

## 2. アクター (Actor)
- ACT-001: オペレーター (Operator)
- ACT-002: メンテナンス担当 (MaintenanceCrew)

## 3. ハードウェア (Hardware)
- HW-001: 駆動ホイール (Wheels)
- HW-002: LIDARセンサー (Lidar)
- HW-003: バッテリー (Battery)
- HW-004: グリッパーアーム (Gripper)

## 4. データ (Data)
- DATA-001: 倉庫マップ (MapData)
- DATA-002: バッテリー残量 (SoC)

## 5. 機能 (Function)
- FUNC-001: 棚Aへ移動
  - DATA-001 (MapData) と HW-002 (Lidar) を使用し、HW-001 (Wheels) を制御する。
- FUNC-002: 物品ピックアップ
  - HW-004 (Gripper) を制御する。
- FUNC-003: 梱包エリアBへ移動
  - `FUNC-001` と同様のロジック。
- FUNC-004: バッテリー残量監視
  - HW-003 (Battery) から `DATA-002 (SoC)` を更新する。
- FUNC-005: 充電ステーションへ移動
  - DATA-002 (SoC) が20%未満でトリガー。HW-001 (Wheels) を制御する。

## 6. 要件 (Requirement)
- REQ-001: ボットは棚AからエリアBへ物品を運ぶこと。(FUNC-001, 002, 003が満たす)
- REQ-002: バッテリー残量が少なくなったら自動で充電しに戻ること。(FUNC-004, 005が満たす)

## 7. 制約 (Constraint)
- CONST-S-001: 緊急停止 (Safety)
  - 障害物を検知した場合、100ms以内に停止する。
  - (APPLIES_TO: FUNC-001, FUNC-003, FUNC-005)
- CONST-P-001: 動作速度 (Performance)
  - 移動機能の最大速度は 1.0 m/s とする。
  - (APPLIES_TO: FUNC-001, FUNC-003, FUNC-005)
- CONST-P-002: ピックアップ時間 (Timing)
  - 物品ピックアップは 5秒以内に完了すること。
  - (APPLIES_TO: FUNC-002)
- CONST-P-003: 動作速度 (Performance)
  - 安全のため、ピックアップ時の移動速度は 0.1 m/s を超えてはならない。
  - (APPLIES_TO: FUNC-001, FUNC-003, FUNC-005)