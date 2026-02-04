AUTOSAR OS의 **Scalability Class(SC)**는 운영체제 기능을 그룹화하여 애플리케이션의 요구사항과 하드웨어 성능에 따라 최적화된 OS를 구성할 수 있도록 정의된 4가지 클래스입니다.

각 Scalability Class에 대한 상세 설명은 다음과 같습니다.

### 1. Scalability Class의 구성 및 특징

*   **Scalability Class 1 (SC1):** 
    *   **OSEK OS**의 모든 기능(고정 우선순위 기반 스케줄링 등)과 **Planned Schedules(Schedule Tables)** 기능이 포함됩니다.
    *   별도의 보호 메커니즘(메모리, 타이밍)이 없으며, 알람 콜백(Alarm Callback) 기능은 SC1에서만 허용됩니다.
*   **Scalability Class 2 (SC2):** 
    *   **SC1의 기능 + 타이밍 보호(Timing Protection)** 기능이 추가됩니다.
    *   실행 시간 예산(Execution Budget), 태스크 활성화 빈도, 리소스 잠금 시간 등을 감시하며, 이를 위해 고우선순위 인터럽트를 지원하는 하드웨어 타이머가 필요합니다.
*   **Scalability Class 3 (SC3):** 
    *   **SC1의 기능 + 메모리 보호(Memory Protection)** 기능이 추가됩니다.
    *   결함 격리 및 복구를 위한 **OS-Application**, 서비스 보호(Service Protection), 신뢰 함수(CallTrustedFunction) 등을 지원합니다.
    *   하드웨어적으로 **MPU(Memory Protection Unit)**가 반드시 필요합니다.
*   **Scalability Class 4 (SC4):** 
    *   **SC1 + SC2 + SC3**의 모든 기능을 포함하는 최상위 클래스입니다.
    *   타이밍 보호와 메모리 보호 기능을 모두 제공하여 시스템 안정성을 극대화합니다.

### 2. 주요 기능별 비교 및 제약 사항

| 주요 기능 | SC1 | SC2 | SC3 | SC4 | 하드웨어 요구사항/비고 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **OSEK OS 기능** | 지원 | 지원 | 지원 | 지원 | 모든 클래스 공통 |
| **Schedule Tables** | 지원 | 지원 | 지원 | 지원 | 최소 지원 개수 상이 (SC2/4는 8개 이상) |
| **Stack Monitoring** | 지원 | 지원 | 지원 | 지원 | 스택 오버플로우 감시 |
| **Protection Hook** | 미지원 | 지원 | 지원 | 지원 | 보호 오류 발생 시 호출 |
| **Timing Protection** | 미지원 | **지원** | 미지원 | **지원** | 하드웨어 타이머 필요 |
| **Memory Protection** | 미지원 | 미지원 | **지원** | **지원** | **MPU** 필수 |
| **OS-Applications** | 선택* | 선택* | **필수** | **필수** | 결함 컨테인먼트 영역 정의 |

*   **멀티코어(Multi-Core) 시스템에서의 특이점:** 싱글코어에서는 SC1/SC2에서 OS-Application이 선택 사항이지만, **멀티코어 환경에서는 Scalability Class와 무관하게 OS-Application 사용이 의무화**됩니다.
*   **하드웨어 의존성:** SC3와 SC4는 하드웨어의 MPU 및 권한 모드(Privileged/Non-privileged modes) 지원이 필수적이며, 하드웨어 지원이 없는 마이크로컨트롤러에서는 구현할 수 없습니다.
*   **상위 호환성:** 하위 Scalability Class 구현체라 하더라도 상위 클래스의 기능을 일부 지원할 경우, 해당 인터페이스는 반드시 AUTOSAR OS 표준 사양을 준수해야 합니다.

요약하자면, **SC1**은 기본 기능, **SC2**는 시간 관리 강화, **SC3**은 공간(메모리) 분리 강화, **SC4**는 전체 보호 기능을 제공하는 체계입니다.