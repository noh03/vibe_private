아래는 이전에 제시했던 근거 출처들을 기준으로, 텍스트로 복사 가능한 링크(원문 URL) 와 함께 출처 내 정확한 위치(페이지/절/요구사항 ID/문장) 를 “근거-매핑” 형태로 정리한 것입니다.
(표기 규칙: p.X/Y = PDF 뷰어에 표시되는 X of Y 페이지 기준, § = 문서 절(Section), SWS_* = AUTOSAR 요구사항 ID)


---

1) 복사용 링크(원문 URL)

[AUTOSAR] Overview of Functional Safety Measures in AUTOSAR (R22-11)
https://www.autosar.org/fileadmin/standards/R22-11/CP/AUTOSAR_EXP_FunctionalSafetyMeasures.pdf

[AUTOSAR] Specification of Operating System (R22-11)
https://www.autosar.org/fileadmin/standards/R22-11/CP/AUTOSAR_SWS_OS.pdf

[AUTOSAR] Timing Analysis (R22-11)
https://www.autosar.org/fileadmin/standards/R22-11/CP/AUTOSAR_TR_TimingAnalysis.pdf

[AUTOSAR] Overview of Functional Safety Measures in AUTOSAR (R4.3.1)
https://www.autosar.org/fileadmin/standards/R4.3.1/CP/AUTOSAR_EXP_FunctionalSafetyMeasures.pdf

[Vector] 혼합형 ASIL 시스템의 성공적인 구현 (PDF)
https://cdn.vector.com/cms/content/know-how/_technical-articles/Safety_ElektronikAutomotive_201307_PressArticle_KO.pdf

[Beningo] Is RTOS Performance affected by an MPU?
https://www.beningo.com/is-rtos-performance-affected-by-an-mpu/

[Infineon] AURIX TC3xx Documentation – FuSa in a Nutshell (Protection sets / context switch)
https://documentation.infineon.com/aurixtc3xx/docs/kbq1745576121130

[ST] AN3423 – Shrinking the AUTOSAR OS: code size and performance optimizations (PDF)
https://www.st.com/resource/en/application_note/an3423-shrinking-the-autosar-os-code-size-and-performance-optimizations-stmicroelectronics.pdf


---

2) 출처별 “근거 위치” 상세(페이지/절/문장/요구사항)

A. AUTOSAR EXP: Functional Safety Measures (R22-11)

1. “ASIL이 다른 SW-C는 같은 OS-Application에 두지 말아야 한다” + “같은 OS-App 내부는 Memory Partitioning만으로 간섭배제 불가”



위치: p.14/93, §2.1.2.4 Memory Partitioning within Application Software

원문 핵심 문장(요지):

“Software Components with different ASIL ratings should not be assigned to the same OS-Application.”

“Memory Partitioning does not provide freedom from interference … within the same OS-Application.” 



2. “SW-C 내부(같은 SW-C의 Runnable들)까지 분리하려면 OS-App 레벨 partitioning만으론 부족 → Task-level partitioning 필요”



위치: p.15/93, §2.1.2.5 Memory Partitioning within Software Components

원문 핵심 문장(요지):

“Memory Partitioning cannot be used to separate Runnables within the same SW-C … partitioning has to be performed at Task-level.” 



3. “Task-level partitioning은 ‘may’로 옵션(모든 OS가 지원하지 않을 수 있음)”



위치: p.16/93, §2.1.2.5 하단(표/설명)

원문 핵심 문장(요지):

“implementation of Task-level partitioning is optional … not every AUTOSAR OS implementation may support …” 



> 위 1)~3) 조합이 “요구사항 만족(ASIL 혼재, FFI 확보)을 위해 OS-App 분리 + (SC4 기반) 보호기능 활성화가 사실상 강제” 라는 논리의 핵심 근거입니다.




---

B. AUTOSAR SWS: OS Specification (R22-11)

1. SC4(Scalability Class 4)에서 제공/요구되는 주요 기능(예: Memory Protection=MPU, Privileged/Non-privileged, Timing Protection 등)



위치: p.120/335, Table 7.4: Scalability classes

표 내부 핵심 항목(요지):

“Memory Protection … MPU”

“(Non-)privileged Modes …”

“Timing Protection … timer(s) with high priority interrupt …” 



2. Memory Protection의 보호 범위 한계(= OS가 관리하는 ‘객체’ 단위 / 동일 Task·ISR 내부 호출 함수 간 보호는 불가)



위치: p.64/335, §7.7 Memory Protection Scheme

원문 핵심 문장(요지):

“Protection is only possible for objects … managed by the Operating System module.”

“No protection is possible between functions called from within the same Task/Category 2 ISR.” 



3. OS-Application 간 메모리/스택/데이터 영역 쓰기 접근 차단(대표 요구사항 예시)



위치: p.64~65/335, §7.7.1.2 Requirements

관련 요구사항 ID(예):

[SWS_Os_00355] / [SWS_Os_00356] (OS-App 간 stack/data write access 방지) 



4. Timing Protection이 “Non-trusted OS-Application”에 대해 강제 적용됨(모든 Task/Cat2 ISR에 적용)



위치: p.69~70/335, §7.7.2.2 Requirements

요구사항 ID:

[SWS_Os_00028] In a non-trusted OS-Application … shall apply timing protection to every Task/Category 2 ISR … 



5. MPU/Protection 활성화 시 성능(부하) 증가와 직접 연결되는 OS 구현 메커니즘(랩퍼/모드 전환 오버헤드)



위치: p.79/335, §7.7.4.3 Implementation Notes

원문 핵심 문장(요지):

“additional work … in the interrupt wrapper …”

“on every entry … switch to non-privileged mode … may affect performance.” 



> (2)+(5)가 “MPU 활성화 시 CPU load가 증가하는 구조적 이유(모드전환/랩퍼/검사/설정 오버헤드)” 를 AUTOSAR OS 관점에서 직접 뒷받침합니다.




---

C. AUTOSAR TR: Timing Analysis (R22-11)

1. 코어 CPU load가 사전 정의된 한계를 초과하지 않도록 분석/검증해야 함(요구/가이드 수준의 핵심 문장)



위치: p.18/95, Chapter 3.1.1 Project-specific and general performance indicators (KPIs)

원문 핵심 문장(요지):

“analyze the load on the CPU core(s) shall not exceed the predefined limit.” 



2. 멀티코어 관련 분석 주제(멀티코어 지원/타이밍/부하 관련 챕터 엔트리)



위치: p.22/95, Chapter 3.4 Multicore support (챕터 표기) 


> 이 TR은 “부하 80% 제한” 같은 프로젝트 KPI를 타이밍/부하 분석 항목으로 정식화할 때 근거로 쓰기 좋습니다.




---

D. AUTOSAR EXP: Functional Safety Measures (R4.3.1)

(구버전이지만, R22-11과 동일한 논지(FFI, OS-App 분리, MPU 필요) 가 반복 확인됩니다.)

1. Trusted vs Non-trusted OS-Application 차이(보호기능/권한/타이밍 enforce)



위치: p.10/96, (OS-Application 클래스 설명 문단)

핵심 요지: Non-trusted는 “보호/모니터링 비활성화 불가, timing behavior enforced, privileged mode 금지” 


2. “ASIL이 다른 SW-C는 동일 OS-Application에 두지 말아야” + “동일 OS-App 내는 partitioning만으로 FFI 보장 불가”



위치: p.12/96 부근(OS-Application 언급 문단) 


3. “현대 MCU는 Memory partitioning을 MPU로 지원” (MPU 필요성 직접 언급)



위치: p.16/96 근방(“Implementation of Memory Partitioning” 도식/설명)

핵심 요지: “Modern microcontrollers … support memory partitioning via … MPU.” 



---

E. Vector Informatik 기술기사(PDF): 혼합형 ASIL 시스템의 성공적인 구현

1. OS-Application 분할 + 메모리 파티션 + MPU로 차단(구조 설명)



위치: p.3/7, (본문 “보호 기능/분할/파티션” 설명 문단)

핵심 요지:

“기능 그룹을 OS 어플리케이션으로 분할… 각 OS 어플리케이션 데이터는 별도 메모리 파티션… 액세스는 MPU로 차단” 



2. 컨텍스트 스위치 때 MPU 재구성(= 성능/부하 증가의 직접 원인)



위치: p.3/7, (컨텍스트 전환 설명 문단)

핵심 요지:

“작업/ISR 전환 시 컨텍스트 전환… MPU는 전환 후 활성 작업/ISR 파티션만 사용하도록 재구성” 



3. 그림 캡션으로 “MPU 재구성은 OS를 통해 이루어진다” 명시



위치: p.4/7, [그림 2] 캡션 문장

원문(그대로 요지):

“MPU 의 재구성은 OS 를 통해 이루어진다” 




---

F. Beningo Embedded Group (웹 문서): Is RTOS Performance affected by an MPU?

위치: 본문 중간 문장(HTML 라인 기준 L68)

핵심 요지:

“RTOS task switch 때 MPU 레지스터 재구성이 필요… context switch time 증가… 오버헤드 고려 및 최적화 필요” 




---

G. Infineon Technologies (웹 문서): AURIX TC3xx Documentation (FuSa in a Nutshell – protection sets)

위치: 본문 문장(HTML 라인 기준 L596)

핵심 요지:

“protection sets … permissions 결정”

“hardware efficiently manages the changing of protection sets during task context switches …” 



> 이 문장은 컨텍스트 스위치 과정에서 권한/보호 세트 전환이 ‘하드웨어적으로’ 관리된다는 점을 명시해서, “왜 MPU/보호 기능이 컨텍스트 스위치/부하에 영향을 주는지” 논리 연결에 유용합니다.




---

H. STMicroelectronics (PDF): AN3423 Shrinking the AUTOSAR OS

위치: p.1/13, 1 Introduction

핵심 요지:

“OS 기능은 SC4까지 제공 가능하지만(disadvantage)… (SC4가 커지고 느려질 수 있음)라는 문제의식 제시” 




---

3) (사용자 문서 작성 시) 위 근거를 어떻게 “문장”으로 붙이면 좋은가

“ASIL-B 기능과 QM 기능이 공존하는 시스템에서 FFI(간섭배제) 를 만족하려면, ASIL이 다른 SW-C를 동일 OS-Application에 배치하지 말아야 하며, OS-Application 간 보호를 위해 Memory Partitioning(=MPU 기반) 이 필요하다.”
→ 근거: AUTOSAR EXP R22-11 p.14/93 §2.1.2.4 

“SC4는 Memory Protection(=MPU), (Non-)privileged mode, Timing Protection 등을 포함하며, Non-trusted OS-Application은 모든 Task/Cat2 ISR에 대해 Timing Protection이 강제 적용된다.”
→ 근거: AUTOSAR SWS OS R22-11 p.120/335 Table 7.4, p.69~70/335 §7.7.2.2 [SWS_Os_00028] 

“MPU/보호 기능 활성화는 컨텍스트 스위치/ISR 진입에서 랩퍼 처리 및 권한 전환 등 추가 오버헤드를 발생시켜 CPU load 상승 요인이 된다.”
→ 근거: AUTOSAR SWS OS R22-11 p.79/335 §7.7.4.3, Vector 기사 p.3/7(컨텍스트 전환 시 MPU 재구성) 



---

원하면, 위 “근거-매핑”을 그대로 사용해서 당신 프로젝트용 보고서 형태(예: ‘현황→문제정의→규격근거→원인분해→ASW/BSW 체크리스트→대책별 적용가이드→리스크/검증계획’) 로 재구성해 드릴게요.