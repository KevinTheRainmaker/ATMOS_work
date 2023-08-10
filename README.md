# LI-COR CO2 데이터 자동 다운로드 프로그램

## Project Description

GIST 지구환경공학과 ATMOS LAB에서 <strong>수동으로 진행하던 CO2 측정 데이터의 다운로드 및 변환을 자동화</strong>함으로써 반복작업에 소요되는 시간과 노력을 줄이고자 진행한 프로젝트입니다.

파이썬 언어를 이용하여 코드를 작성했고, Pyinstaller를 이용하여 실행파일(.exe)을 빌드함으로써 <strong>파이썬이 설치되어 있지 않은 환경에서도 손쉽게 실행</strong>시킬 수 있도록 하였습니다.

## Process Overview

### 0. 스케쥴 확인

프로그램을 실행시킬 경우 콘솔창이 뜨며 다음 실행 시간을 디스플레이하게 됩니다. 해당 스케쥴은 `time_set.json`에서 조정할 수 있으며, 이를 수정한 후에는 <strong>프로그램을 재실행</strong>해야 합니다.

`time_set.json`의 구조는 다음과 같습니다.

```
{
  "DEFAULT": {
    "REPEAT_TYPE": "day", /* [day, hour, minute] can be selected here */
    "SCHEDULE_SETTING": "23:50",
    "TIME_BUFFER": "10" /* from today - TIME_BUFFER */ 
  }
}
```

이 중 `REPEAT_TYPE`은 자동 반복을 어떤 모드로 실행할지를 결정하는 부분으로, `day`, `hour`, `minute` 중 하나로 설정하시면 됩니다. `day`의 경우 24시간 형식 타임라인 중 언제 실행할지를 설정할 수 있는 모드로, '23:50'으로 설정할 경우 매일 컴퓨터 시간 기준 23:50분에 자동화가 작동되게 됩니다. `hour`과 `minute` 모드로 설정할 경우 실행 시간을 기준으로 n시간 후, n분 후 자동화가 작동하게 됩니다.

추가) TIME_BUFFER가 추가되었습니다. 실행일을 기준으로 n일만큼을 과거로 더하여 다운로드 할 수 있습니다.
추가) JSON 파일에 주석을 달 수 있도록 하였습니다. C언어의 주석 스타일을 차용하여, /* 와 */로 감쌀 경우 해당 기호 내부는 주석으로 작동합니다.
추가) TIME_BUFFER의 에러가 해결되었습니다. 기존 방식은 TIME_BUFFER에 의해 계산되는 날짜가 현재 날짜의 연, 월을 초과할 경우 정상적으로 작동하지 않았지만 해당 에러가 수정되었습니다.

프로그램 동작이 멈추지 않았음을 시각화 하기 위해 로테이션을 구현해두었으며, 해당 로테이션이 멈추지 않았다면 정상 동작하고 있는 것입니다.

<br>

### 1. 접속 확인

데이터를 받아오기 위한 서버는 고산 지대에 위치하여 있기에 네트워크 에러가 일어날 수 있습니다. 따라서 scp 명령어를 통해 데이터를 받아오기 전, ssh 명령어를 통해 <strong>접속 가능 여부를 테스트</strong> 합니다. ssh 접속이 불가할 경우 30초 후 재시도하도록 하였습니다.

<br>

### 2. 데이터 다운로드

접속 가능이 확인될 경우 scp 명령어를 이용하여 데이터 다운로드를 시도합니다. 파이썬 scp 패키지의 SCPClient를 이용하여 scp 인스턴스를 만들고 progress 함수를 이용하여 다운로드 상황을 실시간으로 확인할 수 있도록 하였습니다.

이때, 전체 데이터를 다운로드 할 경우 오랜 시간이 소요되므로 <strong>실행 시점을 기준으로 일부 데이터만을 가져오도록</strong> 하였습니다. 다운로드 받는 데이터의 범위는 <strong>실행일에서 마지막 숫자를 잘라낸 날짜의 데이터</strong>입니다. 예를 들어, 06/04일에 다운로드를 받을 경우 다운로드 범위는 06/01~06/04입니다.

데이터 다운로드가 완료될 경우 ssh client 인스턴스와 scp client 인스턴스를 close하고 연결을 종료합니다.

<br>

### 3. 데이터 변환

다운로드 받게 되는 데이터는 <strong>txt 포맷의 summary와 ghg 포맷의 raw 데이터</strong>입니다. 이 중 ghg 포맷은 <strong>LI-COR Biosciences의 커스텀 파일 포맷</strong>으로, 정보를 담은 .data 파일을 포함하고 있는 archive 파일입니다. 이를 사람이 확인 가능한 csv 포맷으로 변환하기 위해서는 이를 압축 해제하여 .data 파일을 추출한 후 열 별로 읽어와서 csv로 저장해야 합니다.

\* 관련 공식문서: https://www.licor.com/env/support/EddyPro/topics/ghg-file-format.html

전체를 압축해제 할 경우 불필요한 데이터가 모두 나오게 되어 번잡해지므로 .data 포맷만을 가져올 수 있도록 하였습니다. .data 포맷은 헤더를 가진 ASCII 테이블 형태로, 공식 사이트에서는 변환 시 메타 데이터 또한 필요하다고 명시되어 있으나 실험 결과 메타 데이터 없이도 무난히 변환이 수행되는 것을 확인했습니다.

다만, <strong>일부 데이터의 경우 data 추출이 실패하는 경우가 발생</strong>했기에, 이를 예외 처리하여 failed list에 추가하도록 하였습니다.

data-to-csv 변환이 완료된 이후에는 저장 공간 절약을 위해 <strong>csv 외 포맷을 삭제</strong>하도록 하였습니다. 다만 이때 failed list에서 관리되는 파일의 경우 별도의 처리 작업을 할 수 있도록 삭제를 하지 않도록 하였습니다.

<br>
<!--
### 4. 드롭박스 업로드
드롭박스 API를 이용해 실행 로그파일과 데이터를 지정된 드롭박스에 업로드하도록 하였습니다. 초기에는 Access Token만을 이용하였기에 Expiration time이 지나게 되면 접속이 불가해지는 이슈가 있었기에 Postman을 통한 HTTP 리퀘스트를 보내어 Refresh Token을 발급 받아 추가로 이용함으로써 Access Token을 갱신할 수 있도록 하였습니다.
해당 토큰 값은 `config.json`에 저장되어 있으며, <strong>해당 파일 내의 정보는 외부 공개되지 않도록 주의해주시기 바랍니다.</strong> (외부 공개될 경우 공격으로부터 사용자를 보호하기 위해 토큰이 삭제될 수 있습니다.)
데이터의 디렉터리 구조는 다음과 같으며, 기본적으로 서버측 데이터 구조와 동일합니다.
```
Dropbox
    └── CO2
        ├── log.txt
        ├── csv
        |    ├── 2023-06-04T230000_AIU-1905.csv
        |    └── ...
        ├── raw
        |   └── 2023
        |       ├── 05
        |       └── 06
        |           └── [failed GHGs]
        └── summaries
            ├──2023-06-04_AIU-1905_EP-Summary.txt
            └── ...
```
데이터 업로드가 완료되는 경우 데이터가 업로드된 시각을 로그에 기록한 후 콘솔에 출력된 내용을 지우고 0번으로 돌아가게 됩니다.
최종 로그의 예시는 다음과 같습니다.
<img width="450" alt="image" src="https://github.com/KevinTheRainmaker/ATMOS_work/assets/76294398/435060fa-bcda-40ec-b851-e78c11c4c712">
<br>
-->

## Future Works

### 1. GUI 구현
해당 프로그램은 빠른 개발과 간편한 실행만을 목표로 제작되었기에 GUI를 별도로 구현하지 않았습니다. 사용에는 문제가 없으나 직관성을 위해서는 이를 개선할 수 있을 것으로 보입니다. GUI로 제작할 경우 <strong>시간 및 모드 설정이 더욱 직관적</strong>일 것으로 생각되며, <strong>config 값 또한 프로그램 내부에 숨길 수 있을 것</strong>으로 보입니다.

### 2. 디지털 서명
개인이 개발한 프로그램이기에 <strong>백신 등 보안 소프트웨어에서 위험으로 판단하여 삭제 혹은 실행을 거부</strong>할 수 있습니다. 따라서 이와 같은 상황이 발생할 경우 해당 프로그램을 <strong>보안 조치 예외로 등록</strong>해주어야 합니다. 이와 같은 번거로움을 해소하게 위해서는 디지털 서명을 추가해주는 등의 조치를 취할 수 있습니다.

### 3. 파라미터 주입 경로 추가
현재 버전은 데이터 경로를 포함한 다수의 파라미터들이 코드 내부에서 주입되고 있어 실행 파일 차원에서 관리하기 어려운 부분이 있습니다. 필요한 파라미터를 잘 선별하여 외부에서 주입할 수 있도록 코드를 수정하면 더욱 유연한 사용이 가능할 것이라 생각됩니다.
