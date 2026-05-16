# Application License Notice

## Thingswell Inc. Proprietary Internal Test License

**Effective Date:** 2026  
**Licensor:** Thingswell Inc.  
**Product:** Multimodal Emotion Recognition & Korean STT Monitor  
**Version:** Beta Test Release v0.1.0  
**Contact:** hjlee@thingswell.co.kr  

---

## 1. Grant of License / 라이선스 부여

Thingswell Inc. grants the authorized tester a limited, non-exclusive, non-transferable,
revocable license to use this software solely for the following purposes:

Thingswell Inc.는 승인된 테스터에게 다음 목적에 한해 제한적, 비독점적, 양도 불가능,
철회 가능한 라이선스를 부여합니다:

- Internal testing (내부 테스트)
- Research and development (연구 및 개발)
- Functional verification (기능 검증)
- Reliability testing (신뢰성 시험)
- Performance evaluation (성능 평가)
- Demonstration (데모 및 시연)

---

## 2. Restrictions / 제한사항

The following actions are strictly prohibited without prior written permission
from Thingswell Inc.:

다음 행위는 Thingswell Inc.의 사전 서면 승인 없이 엄격히 금지됩니다:

### 2.1 No Unauthorized Copying / 무단 복제 금지
The software may not be copied, duplicated, or reproduced in any form except for
authorized backup purposes on the tester's designated machine.

### 2.2 No Redistribution / 재배포 금지
The software may not be distributed, shared, uploaded, or transferred to any third
party, public repository, file sharing service, or external network.

### 2.3 No Commercial Resale / 상업적 재판매 금지
The software may not be sold, sublicensed, rented, leased, or otherwise
commercialized in any form.

### 2.4 No Reverse Engineering / 역설계 금지
The software may not be reverse-engineered, decompiled, disassembled, or otherwise
subjected to any process that attempts to derive source code or underlying algorithms
beyond what is provided.

### 2.5 No Public Deployment / 외부 공개 배포 금지
The software may not be deployed on public-facing servers, distributed via app stores,
or made available for public download.

---

## 3. Camera and Microphone Usage / 카메라 및 마이크 사용

This application requires access to:
- **Camera (웹캠):** For real-time face emotion analysis
- **Microphone (마이크):** For voice activity detection, voice emotion analysis, and Korean STT

### Requirements / 요구사항:
- The user must grant camera and microphone permissions for the application to function.
- Testing should not be conducted without the informed consent of all individuals
  whose face or voice may be captured.

### 사용자 동의:
- 이 앱을 사용하려면 카메라와 마이크 접근 권한을 허용해야 합니다.
- 얼굴이나 음성이 캡처될 수 있는 모든 개인의 사전 동의 없이 테스트를 진행하지 마세요.

---

## 4. Face and Voice Data Processing / 얼굴 및 음성 데이터 처리

### 4.1 Data Processing Principles / 데이터 처리 원칙

- Face analysis is performed locally in real-time. Raw image frames are not stored.
- Voice analysis is performed locally. Raw audio is not stored after processing.
- STT results are processed in memory and may be logged in text form only.
- Performance metrics and analysis results may be logged for testing purposes.

### 4.2 주의사항 / Precautions

- 얼굴 인식 결과는 감정 분류 목적으로만 사용됩니다.
- 의료, 법률, 채용, 고위험 의사결정에 사용하지 마세요.
- 테스트 로그에 개인 식별 정보가 포함되지 않도록 주의하세요.
- 로그를 외부로 전송하거나 공유하기 전 민감 정보를 검토하세요.

### 4.3 Cautions

- Face recognition results are for emotion classification purposes only.
- Do not use for medical, legal, hiring, or high-stakes decision making.
- Ensure test logs do not contain personally identifiable information.
- Review logs for sensitive information before transmitting or sharing externally.

---

## 5. Disclaimer of Warranty / 보증 부인

THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE, AND NONINFRINGEMENT.

본 소프트웨어는 상품성, 특정 목적에의 적합성, 비침해에 대한 보증을 포함하되
이에 한하지 않는 어떠한 명시적 또는 묵시적 보증 없이 "있는 그대로" 제공됩니다.

IN NO EVENT SHALL THINGSWELL INC. BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM,
OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

어떠한 경우에도 Thingswell Inc.는 본 소프트웨어의 사용 또는 소프트웨어와 관련하여
발생하는 계약, 불법행위 또는 기타 소송에서의 어떠한 청구, 손해 또는 기타 책임에 대해
책임을 지지 않습니다.

---

## 6. Termination / 종료

This license is effective until terminated. Thingswell Inc. may terminate this license
at any time without notice. Upon termination, the tester must cease all use and
destroy all copies of the software.

이 라이선스는 종료될 때까지 유효합니다. Thingswell Inc.는 사전 통보 없이 언제든지
이 라이선스를 종료할 수 있습니다. 종료 시 테스터는 모든 사용을 중단하고
소프트웨어의 모든 사본을 파기해야 합니다.

---

## 7. Open Source Components / 오픈소스 구성 요소

This application utilizes various open-source libraries and frameworks.
Each open-source component retains its original license terms.
This Application License Notice applies only to the proprietary application code
developed by Thingswell Inc. and does not override or modify the licenses of any
open-source dependencies.

이 애플리케이션은 다양한 오픈소스 라이브러리 및 프레임워크를 활용합니다.
각 오픈소스 구성 요소는 원래의 라이선스 조건을 유지합니다.
이 Application License Notice는 Thingswell Inc.가 개발한 독점 애플리케이션 코드에만
적용되며, 오픈소스 의존성의 라이선스를 대체하거나 수정하지 않습니다.

---

## 8. Governing Law / 준거법

This license shall be governed by and construed in accordance with the laws of
the Republic of Korea.

이 라이선스는 대한민국 법률에 의해 규율되고 해석됩니다.

---

**Thingswell Inc.**  
AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.  
Contact: hjlee@thingswell.co.kr  
Website: https://thingswell.co.kr
