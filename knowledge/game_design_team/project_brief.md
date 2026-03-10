# Game Design Team Project Brief

이 문서는 `game_design_team` crew가 항상 참고해야 하는 고정 프로젝트 컨텍스트다.  
기준 문서는 `HackSlClient` 프로젝트 README다.

---

# 고정 게임 컨셉

- 이 프로젝트는 **Unity ECS(DOTS) 기반 액션/전투 중심 클라이언트**다.
- 전투 구조는 **뱀서라이크 + Brotato 스타일의 즉시성 있는 전투**를 기반으로 한다.
- 여기에 `Path of Exile`, `Diablo` 계열의 **빌드 준비 중심 성장 구조**를 결합한다.
- 플레이어는 장비를 수집하는 캐릭터가 아니라 **소수의 장비를 조율하는 전투 대장장이(combat blacksmith)**다.
- 핵심 경험은 **아웃게임에서 만든 빌드를 2분 전투에서 검증하는 것**이다.

핵심 문장

> "나는 장비를 줍는 사람이 아니라, 장비를 완성하는 사람이다."

---

# 핵심 플레이 루프

Outgame Build  
→ Arena Battle (~2 minutes)  
→ Result Report  
→ Crafting / Build Adjustment  
→ Next Battle

핵심 목적

- 빌드 설계
- 전투 검증
- 보상 기반 제작
- 다음 빌드 개선

핵심 경험

**Forge → Test → Analyze → Improve**

---

# 전투 구조

- 전투 시간은 **약 2분 내외**로 설계한다.
- 목표는 **생존 + 적 처치 + 효율적인 점수 획득**이다.
- 전투 중에는 **레벨업 / 스킬 선택 / 빌드 변경이 없다**.
- 전투 성능은 **전투 전 빌드 준비 + 플레이 컨트롤**로 결정된다.
- 시간이 지날수록 전투 강도는 점점 상승한다.

전투는 단순 난이도 상승이 아니라  
**빌드 성능을 시험하는 테스트 공간**이어야 한다.

---

# Lyric Chain 시스템

이 게임의 핵심 차별점은 **Lyric Chain 시스템**이다.

장비 옵션은 단순 스탯이 아니라  
**전투 중 연결되는 체인 구조의 문법 요소**다.

각 옵션은 두 가지 속성을 가진다.

Tag  
예: Projectile, Bleed, Chain, Dash, Crit, Shield

Syntax Role  
예: Starter, Amplifier, Converter, Finisher, Echo

플레이어 목표

- 높은 수치가 아니라
- **의도한 체인이 안정적으로 작동하는 빌드 설계**

---

# 장비 철학

이 게임은 **장비 수집 게임이 아니다.**

핵심 원칙

- 장비 수는 적게 유지
- 옵션 조합 깊이는 크게 유지
- 장비는 오래 사용하도록 설계

기본 장비 슬롯

- Weapon
- Armor
- Core
- Accessory

각 슬롯은 특정 역할을 선호한다.

예

Weapon → Starter / Finisher  
Armor → Sustain / Echo  
Core → Converter  
Accessory → Amplifier / Utility

장비 정체성은 **아이템 수가 아니라 옵션 조합에서 나온다.**

---

# Crafting 시스템 개요

플레이어는 장비 옵션을 다음 방식으로 조정한다.

Engrave  
→ 옵션 생성

Reinforce  
→ 옵션 강화 / 체인 안정성 증가

Mutate  
→ 태그 또는 역할 변이

Seal  
→ 옵션 고정

주요 재료

- Engraving Shard
- Amplifier Catalyst
- Prism
- Seal
- Tag Essence

Crafting은 **완전 랜덤이 아니라 통제 가능한 제작 경험**이어야 한다.

---

# 전투 후 Build Report

전투 결과는 단순 점수가 아니라  
**빌드 분석 리포트** 역할을 한다.

예시 정보

- Tag activation ratio
- Chain success rate
- Chain break 위치
- 부족한 역할
- 추천 제작 방향

목적

**전투 → 제작 → 다음 빌드 설계** 루프 강화

---

# 콘텐츠 방향

콘텐츠 가치는 **스테이지 수가 아니라 빌드 실험 깊이**다.

확장 축

- 새로운 Tag
- 새로운 Syntax Role
- 새로운 Crafting Rule
- 시즌 체인 메커닉
- Build 공유 코드
- Challenge Arena

---

# 개발 방향

- 목표 플랫폼: **Mobile + Steam(PC)**
- UX / 입력 / 정보 밀도는 **멀티 플랫폼 기준**으로 설계한다.
- 핵심 목표는 **짧은 전투 안에서 빌드 준비의 재미를 극대화하는 것**이다.
- 인게임 전투는 **강한 액션성과 판정 만족감**을 제공해야 한다.

---

# 기술 및 프로덕션 제약

- Engine: **Unity 6**
- Language: **C#**
- Runtime: **Unity ECS (Entities 1.4.x)**
- Physics: **Unity Physics**
- Rendering: **URP**
- Asset Loading: **Addressables**
- UI: **UGUI**
- Input: **Input System**

데이터 구조는 **Data-driven 설계**를 따른다.

예

- UnitData
- SkillData
- EquipData

장비/스킬 효과는 **Modifier + Tag 기반 시스템**을 전제로 한다.

---

# 반드시 유지할 원칙

- 플레이어 판타지는 **전투 대장장이**다.
- 게임 구조는 항상

Outgame Build  
→ Combat Verification  
→ Reward  
→ Build Improvement

루프를 강화해야 한다.

- 전투 시스템은 **빌드 준비의 중요성을 강화해야 한다**.
- 짧은 전투 안에서도 **빌드 차이와 컨트롤 숙련도**가 드러나야 한다.
- 장비 수보다 **옵션 조합과 체인 구조**를 우선한다.

---

# 금지사항

- 전투 중 레벨업 시스템 도입 금지
- 즉석 스킬 선택 시스템 도입 금지
- 랜덤 보상 선택 기반 뱀서 성장 구조 금지
- 전투 내 과도한 메뉴 조작 금지
- 2분 전투 구조와 충돌하는 긴 세션 설계 금지
- 특정 플랫폼 기준 UX 설계 금지
- 이 문서에 없는 프로젝트 고정 사실을 임의로 추가하지 않는다