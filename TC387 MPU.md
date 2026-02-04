아래는 “부하(특히 Core2 91.4%→요구 80% 이하) 개선” 논의를 시작하기 위한 기술 검토/설명 자료(회의용) 초안입니다. 요청하신 대로 **OS SC4(Scalability Class 4) + MPU 적용이 ‘왜 불가피한지’**를 표준 근거 중심으로 정리하고, ASW/BSW 각각의 체크 항목, MPU가 CPU load에 영향을 주는 메커니즘, 항목별 저감 대책 및 적용 가이드까지 포함했습니다. (참고: PDF 스크린샷 기능이 웹 도구 오류로 동작하지 않아, 공개 문서의 텍스트 뷰(라인) 기반으로 인용했습니다.)


---

1. 프로젝트 맥락과 현재 이슈 요약

대상: 차량용 제어기 SW 개발 프로젝트

MCU/코어: TC387 멀티코어 4개 Core0~3 모두 사용

기능 안전: 주요 기능 2개 중 1개 ASIL-B, 1개 QM

OS: SC4 적용 중

OS-Application 파티션(코어별):

Core0: QM 1개, ASIL-B 1개

Core1: ASIL-B 1개

Core2: QM 1개

Core3: QM 1개


개발환경: 현대오토에버 모빌진 클래식 R4.4.0 (AUTOSAR Classic 기반)

성능 이슈:

Core2 CPU load 91.4% (요구 80% 초과)

MPU 활성화 시 10%p 이상 load 상승(관측)


목표:

1. 안전 요구(ASIL/QM 혼재) 충족을 위해 SC4/MPU를 유지하면서


2. Core2 load를 80% 이하로 내릴 수 있는 현실적인 최적화 옵션을 도출하고


3. 부문별(ASW/BSW/OS/Integration/Safety) 액션을 합의





---

2. 결론부터: SC4 + MPU가 “필수”가 되는 구조적 이유

2.1 혼재 ASIL에서 핵심 키워드: Freedom From Interference(FFI)

AUTOSAR ECU 한 대에 안전 관련(ASIL-B) SWC와 비안전(QM) SWC가 공존하면, ISO 26262 관점에서 서로 간 간섭(특히 메모리/시간/자원)을 통제해야 합니다. AUTOSAR의 기능안전 가이드 문서는 “서로 다른 ASIL 등급 SWC 간 FFI를 보장해야 한다”는 전제를 명시합니다. 

2.2 AUTOSAR에서 ‘격리 단위’는 기본적으로 OS-Application(= Partition)

중요한 함정이 있습니다. AUTOSAR 문서는 메모리 파티셔닝이 OS-Application 레벨에서 수행되며, 서로 다른 ASIL 등급 SWC는 동일 OS-Application에 넣지 말라고 권고합니다. 또한 OS-Application 내부(같은 OS-Application 내) SWC 간에는 기본 파티셔닝만으로 FFI가 안 된다는 점도 명확히 합니다. 

즉, 질문이 “왜 MPU를 켤 수밖에 없나?”라면 답은 다음의 체인으로 정리됩니다.

(요구) ASIL-B와 QM이 공존 → FFI 필요 

(설계) AUTOSAR는 OS-Application 단위로 분리/보호를 제공 

(구현) OS는 다른 OS-Application이 스택/프라이빗 데이터에 쓰기 접근 못하게 막아야 함(요구사항 형태로 명시) 

(하드웨어) 이 “막기”는 현실적으로 MPU 같은 하드웨어 메모리 보호가 있어야 강제 가능 (그리고 주변장치/메모리맵 레지스터 보호도 포함) 


2.3 SC4가 의미하는 바: 보호 기능(메모리/타이밍)을 “체계적으로 켠다”

AUTOSAR OS 스펙은 확장 기능을 “Scalability Class”로 구분하고, SC4는 여러 보호/확장 기능이 포함된 상위 클래스로 운영됩니다(최소 요구치 표/OS-Application 지원 등). 
또한 스펙은 Non-Trusted OS-Application은 런타임에 모니터링/보호 기능을 끈 채로 동작하면 안 된다고 명시합니다(즉, “QM이니까 보호 끄자”가 쉽게 허용되지 않음). 

그리고 타이밍 보호도 Non-Trusted OS-Application에서는 “각 Task/Category2 ISR에 적용”을 요구하는 형태로 서술됩니다. 
→ 실무적으로는 “SC4를 선택한 순간, (1) 메모리 보호(MPU) + (2) 타이밍 보호(추가 감시/인터럽트/훅)가 부하 비용으로 따라온다”가 정직한 그림입니다.


---

3. MPU가 CPU load를 올리는 이유

3.1 가장 전형적인 비용: Context Switch 때 MPU 재설정

RTOS/OS가 태스크를 스위칭할 때, 새 태스크의 메모리 권한에 맞게 MPU 레지스터(혹은 보호 세트)를 재구성해야 합니다. 이 작업은 컨텍스트 스위치 시간 자체를 증가시키며, 하드웨어와 MPU region(혹은 range) 수에 따라 영향이 달라집니다. 

AUTOSAR 안전 OS(상용 SafeContext 계열) 설명 자료에서도, 태스크/ISR 전환 시 컨텍스트 저장 후 MPU를 재구성하여 활성 태스크/ISR의 파티션만 접근 가능하게 한다는 동작이 서술됩니다. 

3.2 AURIX(TC3xx)의 “Protection Set”과 전환 비용의 성격

Infineon Technologies AURIX 계열은 MPU 권한을 빠르게 전환하기 위한 “protection set(보호 세트)” 개념(여러 세트/범위)을 갖고, 작업 전환 시 보호 세트를 바꿔 실행 격리를 보장한다는 설명이 있습니다. 

다만 “하드웨어가 효율적으로 관리한다”는 말이 “비용이 0”은 아닙니다. 실측에서 10%p 이상 상승이 관측된 것은 보통 아래가 함께 존재할 때 흔합니다.

(A) 태스크/ISR 스위치가 매우 빈번함(고주기 태스크, Cat2 ISR 다발)

(B) MPU region/range가 과도하게 쪼개짐(링커 섹션/메모리맵이 파편화)

(C) 타이밍 보호까지 켜져서 감시용 인터럽트/훅/프로텍션 처리가 늘어남 

(D) 보호 위반(트랩)이 간헐적으로 발생(설정 오류/스택 오염/경계 침범)


3.3 “부하 10%p 상승”을 납득 가능한 모델로 재구성

CPU load를 단순화하면,

기존 Load = (유효 실행 시간) / (관측 윈도우)

MPU On 후 Load = (유효 실행 시간 + 추가 OS 오버헤드) / (관측 윈도우)


여기서 추가 OS 오버헤드는 대략 다음 합으로 설명됩니다.

1. 컨텍스트 스위치당 MPU 갱신 비용 × (스위치 횟수)


2. 타이밍 보호 감시 비용(budget/timeframe 체크, protection hook 경로) × (대상 task/ISR 이벤트 수) 


3. (선택) 보호 대상 주변장치(peripheral protection) 설정/검사 비용 



AUTOSAR 타이밍 분석 가이드에서도 타이밍 최적화 KPI로 preemption(선점) 수를 줄여 OS overhead를 줄이고, migration(코어 간 이동)과 scheduling interrupt 수를 줄이라고 명시합니다. 
→ 지금 상황(Core2 과부하 + MPU로 10%p 상승)에서 “가장 먼저 의심해야 할 1순위”는 (스위치/선점/스케줄링 인터럽트가 너무 많다)** 입니다.


---

4. 부하 개선을 위해 “체크할 만한 항목” (ASW / BSW)

아래 체크리스트는 “누가 무엇을 확인해야 하는지”를 바로 회의 안건으로 쓰기 좋게 구성했습니다.


---

4.1 ASW 체크 항목(애플리케이션/알고리즘/주기 설계)

1. Runnable 주기/이벤트 설계 재점검



1ms/2ms 고주기 Runnable이 Core2에 몰려 있는가?

“폴링 기반” 로직이 이벤트 기반(인터럽트→이벤트/알람)으로 바뀔 수 있는가?

동일 데이터에 대해 여러 Runnable이 중복 계산/중복 필터링을 하는가?


2. Runnable-to-Task 매핑과 태스크 내 순서



태스크를 너무 잘게 쪼개 “짧은 실행 + 빈번한 활성화”가 되는지?

같은 OS-Application/QM 영역이라면, 여러 Runnable을 하나의 태스크로 묶어 “스위치 수”를 줄일 수 있는지?
(단, 응답시간/데드라인 요구와 트레이드오프)


3. 계산량 자체(핫스팟)



부동소수점 사용, 큰 테이블/보간, 과도한 루프, memcpy/memmove 다발

상수/룩업 테이블화, 고정소수점화, 루프 언롤/최적화 옵션 적용 가능성

디버그/로깅(특히 고주기) 과다 여부


4. 공유자원(락/ExclusiveArea) 사용



짧은 구간에 락을 자주 걸어 선점/블로킹을 만들고 있지 않은가?

임계구역 내에서 통신/진단/메모리 접근이 과도하지 않은가?



---

4.2 BSW 체크 항목(OS/통신/진단/메모리서비스/MCAL)

1. OS 스케줄링/선점 구조



Preemptive 태스크 수가 과다한가?

높은 우선순위 태스크가 잦은 활성화로 하위 태스크를 잘게 쪼개 선점하는가?

Alarm/Counter 기반 주기 태스크가 너무 많아 “스케줄링 인터럽트”가 과다한가?
(타이밍 분석 문서 KPI: scheduling interrupt 감소 권고) 


2. ISR 구조(Cat1 vs Cat2, ISR 길이, Deferred processing)



Cat2 ISR이 너무 길거나 빈번한가?

ISR에서 본처리를 하고 있어, “ISR 스위치 + 타이밍 보호” 비용이 커지고 있지 않은가?

가능한 경우 ISR은 “플래그/이벤트 set”까지만 하고, 처리는 태스크로 내리는 구조가 가능한가?


3. 통신 스택(Com/PduR/CanIf/CanTp 등) 부하



Rx/Tx main function 주기(예: 1ms) 과도 여부

PDU 라우팅/신호 패킹/언패킹이 Core2에 집중되어 있는가?

진단(DCM/DEM) 주기 처리와 통신 처리 타이밍이 겹쳐 burst 부하가 생기지 않는가?


4. 메모리 서비스(NvM/Fee/Ea) 및 플래시 작업



백그라운드 작업이 Core2에서 돌고 있는가?

Flash/NVM 관련 작업이 짧게 쪼개져 자주 깨어나는 구조인가?


5. MPU 설정/메모리맵(링커 섹션) 파편화



OS-Application별 code/data/stack 섹션이 지나치게 분절되어 “MPU region 수”가 커진 상태인가?

AUTOSAR OS 스펙은 메모리 보호를 위해 코드/변수를 “분리된 섹션”에 매핑하는 전제와 구성 접근을 언급합니다. 
→ 이 전제가 “너무 잘게 분리”로 구현되면, 반대로 전환 비용이 커질 수 있습니다(실무적 트레이드오프).


6. 타이밍 보호 설정값의 현실성



ExecutionBudget/TimeFrame이 너무 타이트해 ProtectionHook 경로를 자주 타는가?

ResourceLockBudget/OsInterruptLockBudget 위반이 간헐적으로 발생하지 않는가?

Non-Trusted OS-Application에 타이밍 보호를 적용하도록 요구하는 서술이 있으므로 , “끄기”가 아니라 “현실적인 budget 설계 + 위반 0”이 핵심입니다.



---

5. “항목별 부하 저감 대책”과 MPU-연관 메커니즘

아래는 회의에서 “옵션 비교”가 가능하도록, **왜 효과가 있는지(메커니즘)**까지 붙였습니다.


---

대책 A: Context switch / preemption / scheduling interrupt를 줄여 MPU 오버헤드를 줄인다

핵심 논리
MPU 오버헤드의 상당 부분은 “스위치 이벤트 수”에 비례합니다(스위치 때 MPU 재설정). 
AUTOSAR 타이밍 분석 가이드는 최적화 KPI로 preemption 수 감소(→OS overhead 감소), migration/스케줄링 인터럽트 수 감소를 제시합니다. 

실행 액션(우선순위 순)

1. Runnable-to-Task 재매핑(ASW+RTE)



고주기 Runnable들을 “같은 태스크 내 순차 실행”으로 묶어 activation 수를 줄임

태스크 수 자체를 줄임(너무 많은 짧은 태스크 → 스위치 폭증)


2. 주기 조정 및 offset 분산



1ms/2ms로 쏠린 주기를 5ms/10ms로 완화 가능한 항목 선별

여러 태스크가 같은 tick에 몰리지 않도록 offset 분산(국부 과부하 완화)


3. 스케줄링 방식 정리



Alarm 기반 주기 태스크가 과도하면 스케줄링 인터럽트가 증가

가능한 곳은 이벤트 기반/배치 처리로 전환


4. ISR “짧게 + Deferred processing”



Cat2 ISR에서 heavy 처리 금지, 이벤트 set 후 태스크 처리

ISR 빈도 자체를 줄이기(하드웨어 필터, 배치 인터럽트 등 가능 시)



---

대책 B: 코어 간 부하 재분배(load balancing) 및 migration 최소화

AUTOSAR 타이밍 분석 가이드는 “load balancing(코어 간)”과 “migration 감소”를 KPI로 명시합니다. 

실행 액션

Core2에 집중된 QM 기능을 Core3로 일부 이동(가능한 태스크/BSW 모듈 선별)

단, 코어 이동은 인터코어 통신/공유 자원 락 비용이 늘 수 있으므로(역효과 가능) “이동 후보”를 아래 기준으로 필터링:

(Good) 독립 계산형, I/O 의존 낮음, 공유 데이터 적음

(Bad) 통신 Rx/Tx 중심, shared buffer 다발, 락/스핀락 빈번




---

대책 C: MPU region/range 설계를 “단순화”하여 전환 비용/복잡도를 줄인다

RTOS는 태스크 전환 시 MPU 레지스터를 재구성할 수 있으며, 재구성해야 할 MPU region 수가 많을수록 컨텍스트 스위치 시간이 증가할 수 있습니다. 

AURIX는 protection set 기반으로 범위/권한을 운용합니다. 


실행 액션(링커/메모리맵 담당 + OS 담당 공동)

1. OS-Application별 섹션을 “필요 이상으로 잘게 쪼개지 않기”



code/data/bss/stack을 OS-App 단위로 묶되, 세부 모듈별 과분절을 줄여 MPU 엔트리 수를 최소화


2. 자주 접근하는 데이터는 가능하면 “동일 권한/동일 파티션”으로 배치



공유 데이터 설계는 특히 조심(읽기/쓰기 권한이 얽히면 MPU 구성이 급격히 복잡해짐)


3. peripheral protection(주변장치 보호) 범위를 현실적으로 구성



OS 스펙은 주변장치 보호를 MPU나 전용 보호 유닛으로 구현할 수 있으며, MPU로 하면 “모든 peripheral 레지스터를 region으로 덮기 어려울 수 있다”는 단점도 언급합니다. 
→ “보호해야 할 peripheral”을 안전 요구 기반으로 최소화/명확화하면 구성 단순화에 도움.



---

대책 D: 타이밍 보호(timing protection) 비용을 “위반 0 + 합리적 budget”으로 안정화

타이밍 보호는 Non-Trusted OS-Application에서 강제 적용되는 형태로 서술됩니다. 
그리고 타이밍 분석 가이드는 “scheduling interrupt 수 감소”도 KPI로 제시합니다. 

실행 액션

1. ExecutionBudget/TimeFrame을 실제 WCET 기반으로 재산정(과도 타이트 금지)


2. ResourceLockBudget/OsInterruptLockBudget 위반 가능성이 있는 경로 제거



임계구역 내 처리 최소화

SuspendOSInterrupts()/DisableAllInterrupts() 사용 패턴 점검


3. ProtectionHook 발생 로그를 “0”으로 만드는 것이 1차 목표



위반이 있으면 “보호 기능이 일을 하는” 것이므로, 그 자체가 load spike 원인이 됩니다.



---

6. 개발 환경 고려한 “상세 적용 가이드”(실무 절차)

아래는 “각 부문이 무엇을 산출해야 하는지”까지 포함한 실행 플로우입니다. (모빌진 클래식의 내부 툴/생성기 옵션 명칭은 공개 문서로 확정할 수 없어, AUTOSAR ECUC/OS 설정 관점의 일반 절차로 기술합니다.)

Step 0. 성능 측정 기준 고정

Load 측정 방식(Idle 측정인지, Trace 기반인지), 측정 윈도우, 시나리오(통신량/진단/온도/전압) 고정

MPU Off/On 비교 시, 로그/트레이스 오버헤드 동일 조건 유지


Step 1. Core2 부하 분해(“핫스팟” 도출)

태스크별 실행 시간/WCET, 활성화 빈도, 선점 횟수, ISR 빈도

BSW main function(Com, PduR, Dcm 등) 주기별 실행 시간

스핀락/리소스 점유 시간, OS 인터럽트 lock 시간

산출물: “Core2 Load Waterfall(태스크/ISR별 %)” + “스위치 이벤트 통계”


Step 2. MPU 오버헤드 원인 분리(스위치 수 vs region 수 vs 타이밍 보호)

1. 스위치 수(태스크 활성화/선점/ISR) 변화 없이 MPU만 On/Off 가능한지 실험


2. MPU region 수(메모리 섹션 구성)를 2~3가지 수준으로 단순화한 빌드 비교


3. 타이밍 보호 이벤트(ProtectionHook, budget overrun)가 있는지 로그로 확인



Step 3. Quick-Win 적용(효과 큰 것부터)

AUTOSAR 타이밍 분석 문서가 제시한 KPI 순서(현장 체감 효과 순)로 가면 실패 확률이 낮습니다. 

(1) preemption 감소 → OS overhead 감소

(2) scheduling interrupt 감소

(3) migration 감소

(4) inter-core communication/버퍼/락 비용 감소

(5) 코드 최적화(핫스팟) 및 주기 조정


Step 4. 안전 요구와의 정합성 확인(안전 담당 필수 참여)

서로 다른 ASIL 등급 SWC를 동일 OS-Application에 넣지 않는 원칙 재확인 

Trusted/Non-Trusted 정책: “성능” 이유로 QM을 trusted로 두는 순간, 격리 약화 리스크가 생김
(OS 스펙은 trusted OS-Application의 경우 보호 기능 비활성 상태 실행 가능성을 언급) 
→ 성능 최적화는 “스위치 감소/구성 단순화”로 풀고, 안전 격리 자체를 약화하는 방향은 마지막 옵션으로 두는 것이 보통 안전합니다.


Step 5. 적용 후 검증

MPU 위반 트랩 0

ProtectionHook(시간/락 예산) 위반 0

요구 시나리오에서 Core2 80% 이하 달성

회귀: 통신 피크/진단 동시/온도 worst 조건에서 재측정



---

7. 회의(부문 간 논의)용 안건과 “요청 자료” 템플릿

아래 6개 자료만 모이면, 1~2회 회의로도 “대책 우선순위 + 담당/일정”까지 내기가 쉬워집니다.

1. OS/BSW 통합 담당



Core2: 태스크/ISR 목록(우선순위, 주기/이벤트, Cat1/2, 스택 크기)

선점 횟수, 스케줄링 인터럽트 수, migration 여부

timing protection 설정값(ExecutionBudget/TimeFrame/LockBudget)과 위반 로그


2. ASW 담당



Core2 탑재 Runnable 목록(주기, 실행시간 평균/최대, 호출 경로)

주기 완화 가능 후보, 통합 가능 후보(같은 태스크로 묶기)


3. 메모리/링커/MPU 담당



OS-Application별 code/data/bss/stack 섹션 맵

MPU region/range 수(보호 세트당 엔트리 수)와 변경 가능 여지


4. 통신/진단 담당



Com/PduR/CanTp/Dcm/Dem main function 주기와 실행 시간

피크 트래픽 조건에서 실행 시간 증가량


5. Safety 담당



FFI 논리(ASIL-B ↔ QM 간 분리 근거), OS-Application 배치의 타당성

“성능 때문에 보호 약화”가 허용 가능한지(보통은 매우 제한적)


6. 시스템/PM



80% 요구의 근거(여유율, 피크 조건, 향후 기능 추가분)

목표 달성 데드라인/릴리즈 영향



---

8. 참고 근거(요약)

서로 다른 ASIL 등급 SWC 공존 시 FFI 필요, OS-Application 단위 파티셔닝, 서로 다른 ASIL은 같은 OS-Application에 두지 말 것, OS-Application 간 메모리 접근 차단 요구 

AUTOSAR OS SC(Scalability Class) 최소 요구(표) 

Non-Trusted OS-Application은 보호 기능 비활성 금지, trusted 관련 서술 

Non-Trusted OS-Application의 타이밍 보호 적용 요구 및 예산/보호훅 메커니즘 

RTOS에서 MPU는 task switch 때 MPU 재구성이 필요해 context switch 시간 증가 가능 

태스크/ISR 전환 시 컨텍스트 저장 후 MPU 재구성(활성 파티션만 접근) 개념 설명 

AURIX 보호 세트/전환 개념(컨텍스트 스위치 시 보호 세트 변경) 

타이밍 최적화 KPI(선점/마이그레이션/스케줄링 인터럽트/자원소모 감소) 

OS에서 peripheral protection을 MPU로 구현할 수 있고, 구성상의 장단점 언급 

타이밍 보호 코드를 제외하면 성능/코드 크기 최적화가 가능하다는(단, 본 건은 SC4 요구로 제외 어려움) 참고 사례 



---

원하시면, 위 내용을 그대로 두고 **“Core2 부하 분해 표(태스크/ISR별, 주기/선점/실행시간/WCET/기여율)”**까지 포함한 회의용 1장 요약(Executive 1-pager) + 상세 부록(기술 근거/체크리스트) 형태로 재구성해드릴게요. (지금은 사용자가 준 정보만으로 작성했기 때문에, 실제 “핫스팟”은 태스크/ISR 리스트가 들어오면 훨씬 정확하게 대책 우선순위를 잡을 수 있습니다.)