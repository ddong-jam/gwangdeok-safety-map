"""화면 틀 (HTML). mount("student" | "teacher") 가 <body> 에 그린다."""
from js import document  # 브라우저 문서 (화면 요소를 만들고 넣는 데 쓴다)

STUDENT_CLASS = ''  # 학생 화면 <body> 에 붙일 꾸미기 이름 (없음)
STUDENT = '''
  <header class="topbar"> <!-- 화면 맨 위 막대 -->
    <a class="brand" href="./"> <!-- 왼쪽 로고 (누르면 처음 화면) -->
      <span class="brand-mark" aria-hidden="true"> <!-- 로고 그림 상자 -->
        <svg viewBox="0 0 32 32"><path d="M16 30c-1-4-10-9-10-17a10 10 0 0 1 20 0c0 8-9 13-10 17z" /><circle cx="16" cy="13" r="4" /></svg> <!-- 지도 핀 모양 로고 -->
      </span> <!-- 로고 그림 상자 끝 -->
      <span class="brand-text"> <!-- 로고 글자 -->
        <strong>광덕신문고</strong> <!-- 사이트 이름 -->
        <small>광덕중·고등학교 위험·불편 신고</small> <!-- 작은 설명 -->
      </span> <!-- 로고 글자 끝 -->
    </a> <!-- 로고 끝 -->
    <div class="topbar-actions"> <!-- 오른쪽 버튼 자리 -->
      <button id="btnReport" class="btn btn-danger" type="button" disabled> <!-- 신고 버튼 (준비될 때까지 잠김) -->
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg> <!-- + 아이콘 -->
        <span>위험/불편 신고</span> <!-- 버튼 글자 -->
      </button> <!-- 신고 버튼 끝 -->
    </div> <!-- 오른쪽 버튼 자리 끝 -->
  </header> <!-- 맨 위 막대 끝 -->

  <main class="layout"> <!-- 본문: 왼쪽 지도 + 오른쪽 패널 -->
    <section class="stage" aria-label="평면도"> <!-- 지도 영역 -->
      <svg id="map" class="map" role="application" aria-label="확대·이동 가능한 평면도"></svg> <!-- 도면이 그려지는 곳 -->
      <div class="stage-top"> <!-- 지도 위쪽 줄 -->
        <nav class="crumbs" id="crumbs" aria-label="현재 위치"></nav> <!-- "캠퍼스 › 건물" 길 표시 -->
        <div class="search" id="search"> <!-- 검색 상자 -->
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4 4" /></svg> <!-- 돋보기 아이콘 -->
          <!-- 아래 두 줄: 반·교실 검색 입력 칸 -->
          <input id="searchInput" type="search" placeholder="반·교실 찾기 (예: 2-1)" autocomplete="off" enterkeyhint="search"
                 aria-label="반이나 교실 이름으로 찾기" aria-controls="searchResults" />
          <ul class="search-results" id="searchResults" role="listbox" hidden></ul> <!-- 검색 결과 목록 (처음엔 숨김) -->
        </div> <!-- 검색 상자 끝 -->
      </div> <!-- 지도 위쪽 줄 끝 -->
      <div class="floorbar" id="floorbar" role="tablist" aria-label="층 선택"></div> <!-- 오른쪽 층 버튼 막대 -->
      <div class="map-tools"> <!-- 왼쪽 아래 확대 도구 -->
        <button class="tool" id="zoomIn" type="button" title="확대" aria-label="확대"><svg viewBox="0 0 24 24"><path d="M12 6v12M6 12h12" /></svg></button> <!-- + 확대 버튼 -->
        <button class="tool" id="zoomOut" type="button" title="축소" aria-label="축소"><svg viewBox="0 0 24 24"><path d="M6 12h12" /></svg></button> <!-- - 축소 버튼 -->
        <button class="tool" id="zoomFit" type="button" title="전체 보기" aria-label="전체 보기"><svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" /></svg></button> <!-- 전체 보기 버튼 -->
      </div> <!-- 확대 도구 끝 -->
      <div class="mode-banner" id="modeBanner" hidden> <!-- 신고 모드일 때 위에 뜨는 안내 띠 -->
        <span class="pulse" aria-hidden="true"></span> <!-- 깜박이는 점 -->
        <span id="modeText">도면에서 위험하거나 불편한 곳을 눌러 위치를 찍어주세요</span> <!-- 안내 글 -->
        <button class="btn btn-ghost-light" id="modeCancel" type="button">취소</button> <!-- 신고 모드 취소 버튼 -->
      </div> <!-- 안내 띠 끝 -->
    </section> <!-- 지도 영역 끝 -->

    <aside class="panel" id="panel"> <!-- 오른쪽 패널 -->
      <section class="ctx" id="ctx"></section> <!-- 건물 카드 또는 층 정보 (파이썬이 채움) -->
      <section class="reports"> <!-- 신고 목록 부분 -->
        <div class="reports-head"> <!-- 목록 머리 -->
          <h2 id="listTitle">신고 현황</h2> <!-- 목록 제목 -->
          <div class="stats" id="stats"></div> <!-- 처리 전·긴급·완료 숫자 -->
        </div> <!-- 목록 머리 끝 -->
        <ul class="report-list" id="reportList"></ul> <!-- 신고 목록 (파이썬이 채움) -->
        <p class="demo-note" id="demoNote" hidden>체험 모드예요. 신고가 이 브라우저에만 저장돼요.</p> <!-- 체험 모드 안내 -->
      </section> <!-- 신고 목록 부분 끝 -->
    </aside> <!-- 오른쪽 패널 끝 -->
  </main> <!-- 본문 끝 -->

  <!-- 신고 작성 -->
  <dialog class="sheet" id="formDialog"> <!-- 신고 창 -->
    <form id="reportForm" method="dialog"> <!-- 신고 입력 양식 -->
      <header class="sheet-head"> <!-- 창 머리 -->
        <div> <!-- 제목 묶음 -->
          <p class="eyebrow" id="formWhere">위치</p> <!-- 신고 위치 (파이썬이 채움) -->
          <h2>위험/불편 신고</h2> <!-- 창 제목 -->
          <p class="who-line" id="formWho" hidden></p> <!-- 로그인한 계정 표시 -->
        </div> <!-- 제목 묶음 끝 -->
        <button class="icon-btn" type="button" data-close aria-label="닫기"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button> <!-- X 닫기 버튼 -->
      </header> <!-- 창 머리 끝 -->
      <div class="sheet-body"> <!-- 창 몸통 (입력 칸들) -->
        <fieldset><legend>무엇을 신고하나요?</legend> <!-- 종류 고르기 -->
          <div class="kinds" id="kindChips"> <!-- 종류 버튼 묶음 -->
            <label class="kind-danger"><input type="radio" name="kind" value="danger" checked /><span><b>⚠️ 위험</b><small>다치거나 사고가 날 수 있어요</small></span></label> <!-- 위험 (기본) -->
            <label class="kind-incon"><input type="radio" name="kind" value="incon" /><span><b>🙁 불편</b><small>위험하진 않지만 불편해요</small></span></label> <!-- 불편 -->
          </div></fieldset> <!-- 종류 고르기 끝 -->
        <fieldset><legend>어떤 문제인가요?</legend><div class="chips" id="catChips"></div></fieldset> <!-- 유형 고르기 (파이썬이 버튼을 채움) -->
        <fieldset><legend id="sevLegend">얼마나 위험한가요?</legend><div class="sev" id="sevChips"></div></fieldset> <!-- 위험도 고르기 (파이썬이 채움) -->
        <label class="field"><span>제목 <em>*</em></span> <!-- 제목 칸 (필수) -->
          <input name="title" required maxlength="60" placeholder="예) 2층 계단 난간이 흔들려요 / 정수기가 고장났어요" /></label> <!-- 60자까지 -->
        <label class="field"><span>정확한 장소</span> <!-- 장소 칸 -->
          <input name="spot" maxlength="60" placeholder="예) 2-3반 앞 복도, 계단실 2" /></label> <!-- 60자까지 -->
        <label class="field"><span>자세한 내용</span> <!-- 내용 칸 -->
          <textarea name="desc" rows="4" maxlength="1000" placeholder="언제부터, 얼마나 위험하거나 불편한지 적어주세요"></textarea></label> <!-- 1000자까지 -->
        <div class="field"><span>사진 (선택)</span> <!-- 사진 칸 -->
          <label class="photo-drop"> <!-- 사진을 고르는 상자 -->
            <input type="file" name="photo" accept="image/*" capture="environment" hidden /> <!-- 사진 파일 고르기 (휴대폰은 뒤 카메라) -->
            <img id="photoPreview" alt="" hidden /> <!-- 고른 사진 미리보기 -->
            <span id="photoHint">사진 추가 · 촬영</span> <!-- 상자 안 글자 -->
          </label> <!-- 사진 상자 끝 -->
        </div> <!-- 사진 칸 끝 -->
        <label class="field"><span>이름 (선택)</span> <!-- 이름 칸 -->
          <input name="reporter" maxlength="30" placeholder="비워두면 익명으로 접수돼요" /></label> <!-- 30자까지 -->
        <div class="notice"> <!-- 신고 전 안내문 -->
          <b>📢 신고 전에 꼭 읽어 주세요</b> <!-- 안내 제목 -->
          <ul> <!-- 안내 목록 -->
            <li>내가 직접 본 위험·불편만 사실대로 신고해요.</li> <!-- 안내 1 -->
            <li id="noticeRecord">신고하면 시간과 이 기기 정보가 함께 기록돼요. (익명이어도 기록돼요)</li> <!-- 안내 2 (로그인 여부에 따라 파이썬이 바꿈) -->
            <li>장난·허위 신고는 선생님이 반려하고 이 기기의 신고를 막을 수 있으며, 학교 생활지도를 받을 수 있어요.</li> <!-- 안내 3 -->
            <li>급하게 다칠 것 같은 일은 신고하고 바로 가까운 선생님께도 말씀드려요.</li> <!-- 안내 4 -->
          </ul> <!-- 안내 목록 끝 -->
          <label class="check"><input type="checkbox" name="pledge" required /><span><b>사실대로 신고합니다</b></span></label> <!-- 약속 체크 (필수) -->
        </div> <!-- 안내문 끝 -->
      </div> <!-- 창 몸통 끝 -->
      <footer class="sheet-foot"> <!-- 창 바닥 -->
        <button class="btn btn-quiet" type="button" data-close>취소</button> <!-- 취소 버튼 -->
        <button class="btn btn-danger" type="submit" id="formSubmit">신고 접수</button> <!-- 접수 버튼 -->
      </footer> <!-- 창 바닥 끝 -->
    </form> <!-- 입력 양식 끝 -->
  </dialog> <!-- 신고 창 끝 -->

  <!-- 학생 로그인 (신고할 때만) -->
  <dialog class="sheet" id="loginDialog"> <!-- 로그인 창 -->
    <header class="sheet-head"> <!-- 창 머리 -->
      <div> <!-- 제목 묶음 -->
        <p class="eyebrow" id="loginPurpose">위험/불편 신고</p> <!-- 왜 로그인하는지 (신고 / 공감) -->
        <h2 id="loginTitle">구글 계정으로 로그인</h2> <!-- 창 제목 -->
      </div> <!-- 제목 묶음 끝 -->
      <button class="icon-btn" type="button" data-close aria-label="닫기"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button> <!-- X 닫기 버튼 -->
    </header> <!-- 창 머리 끝 -->
    <div class="sheet-body"> <!-- 창 몸통 -->
      <p class="login-lead">장난을 막으려고 <b>신고하거나 공감할 때만</b> 로그인해요. 지도와 다른 신고 보기는 로그인 없이 돼요.</p> <!-- 로그인 이유 안내 -->
      <ul class="login-points"> <!-- 안내 목록 -->
        <li>누가 신고했는지는 <b>선생님만</b> 볼 수 있어요. 다른 학생에게는 보이지 않아요.</li> <!-- 개인정보 안내 -->
        <li>이 기기에서는 30일 동안 로그인이 유지돼요. 함께 쓰는 컴퓨터라면 신고 뒤 꼭 로그아웃해요.</li> <!-- 로그인 유지 안내 -->
        <li id="loginDomain" hidden></li> <!-- 학교 계정 제한 안내 (제한이 있을 때만) -->
      </ul> <!-- 안내 목록 끝 -->
      <label class="field" id="demoNameField" hidden><span>이름 (체험 모드)</span> <!-- 체험 모드용 이름 칸 -->
        <input id="demoName" maxlength="30" placeholder="체험 모드라 구글 대신 이름만 넣어요" /></label> <!-- 이름 입력 -->
      <button class="btn btn-google" id="btnGoogle" type="button"> <!-- 구글 로그인 버튼 -->
        <svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.5l6.7-6.7C35.6 2.4 30.2 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.8 6C12.4 13.6 17.7 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.6 5.9c4.4-4.1 7-10.1 7-17.6z"/><path fill="#FBBC05" d="M10.5 28.7c-.5-1.4-.8-3-.8-4.7s.3-3.3.8-4.7l-7.8-6C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7l7.8-6z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.6-5.9c-2.1 1.4-4.9 2.3-8.3 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.8 6C6.6 42.6 14.6 48 24 48z"/></svg> <!-- 구글 G 로고 -->
        <span>Google 계정으로 로그인</span> <!-- 버튼 글자 -->
      </button> <!-- 구글 버튼 끝 -->
    </div> <!-- 창 몸통 끝 -->
  </dialog> <!-- 로그인 창 끝 -->

  <!-- 신고 보기 -->
  <dialog class="sheet" id="detailDialog"><div id="detailBody"></div></dialog> <!-- 신고 자세히 보기 창 (파이썬이 내용을 채움) -->

  <div class="toast" id="toast" role="status" aria-live="polite"></div> <!-- 화면 아래 잠깐 뜨는 알림 -->
'''  # 학생 화면 틀 끝

TEACHER_CLASS = 'teacher'  # 선생님 화면 <body> 에 붙일 꾸미기 이름
TEACHER = '''
  <header class="topbar"> <!-- 화면 맨 위 막대 -->
    <a class="brand" href="./teacher.html"> <!-- 왼쪽 로고 -->
      <span class="brand-mark t-mark" aria-hidden="true">🛡️</span> <!-- 방패 아이콘 -->
      <span class="brand-text"> <!-- 로고 글자 -->
        <strong>선생님 관리</strong> <!-- 화면 이름 -->
        <small>광덕신문고 · 신고 관리</small> <!-- 작은 설명 -->
      </span> <!-- 로고 글자 끝 -->
    </a> <!-- 로고 끝 -->
    <div class="topbar-actions"> <!-- 오른쪽 자리 -->
      <span class="who" id="who"></span> <!-- 로그인한 선생님 이름 -->
      <button class="btn btn-quiet" id="btnLogout" type="button" hidden>로그아웃</button> <!-- 로그아웃 버튼 -->
    </div> <!-- 오른쪽 자리 끝 -->
  </header> <!-- 맨 위 막대 끝 -->

  <!-- 로그인 -->
  <section class="t-login" id="login" hidden> <!-- 로그인 화면 -->
    <form class="t-card" id="loginForm" method="dialog"> <!-- 로그인 양식 -->
      <h1>로그인</h1> <!-- 제목 -->
      <p class="sub" id="loginNote"></p> <!-- 안내 (파이썬이 채움) -->
      <label class="field"><span>이름</span><input name="name" maxlength="30" required placeholder="처리 기록에 남을 이름 (예: 김안전 선생님)" /></label> <!-- 이름 칸 (필수) -->
      <div id="loginShared" hidden> <!-- 공용 모드에서만 보이는 칸들 -->
        <label class="field"><span>이메일</span><input name="email" type="email" autocomplete="username" /></label> <!-- 이메일 칸 -->
        <label class="field"><span>비밀번호</span><input name="password" type="password" autocomplete="current-password" /></label> <!-- 비밀번호 칸 -->
      </div> <!-- 공용 모드 칸 끝 -->
      <label class="check"><input type="checkbox" name="keep" /><span><b>이 기기에서 로그인 유지 (14일)</b><small>내 업무용 컴퓨터에서만 체크하세요. 여러 사람이 쓰는 컴퓨터에서는 체크하지 마세요.</small></span></label> <!-- 로그인 유지 체크 -->
      <p class="t-error" id="loginError" hidden></p> <!-- 오류 표시 -->
      <button class="btn btn-primary" type="submit">들어가기</button> <!-- 로그인 버튼 -->
    </form> <!-- 로그인 양식 끝 -->
  </section> <!-- 로그인 화면 끝 -->

  <!-- 관리 화면 -->
  <main class="t-main" id="app" hidden> <!-- 로그인 뒤 보이는 관리 화면 -->
    <nav class="t-tabs" role="tablist"> <!-- 탭 버튼 줄 -->
      <button role="tab" data-tab="dash" aria-selected="true">📊 대시보드</button> <!-- 대시보드 탭 (기본) -->
      <button role="tab" data-tab="list" aria-selected="false">📋 신고 관리</button> <!-- 신고 관리 탭 -->
      <button role="tab" data-tab="map" aria-selected="false">🗺️ 지도로 보기</button> <!-- 지도 탭 -->
    </nav> <!-- 탭 줄 끝 -->
    <p class="demo-note" id="demoNote" hidden>체험 모드예요. 이 브라우저에서 접수한 신고만 보여요. (README 의 "신고를 모두 함께 보기"를 설정하면 모든 학생의 신고가 모여요)</p> <!-- 체험 모드 안내 -->

    <section class="t-tab" id="tab-dash"> <!-- 대시보드 탭 내용 -->
      <div class="tiles" id="tiles"></div> <!-- 숫자 카드들 (처리 전·긴급 등) -->
      <div class="t-grid2"> <!-- 그래프 두 개를 나란히 -->
        <div class="t-card"><h3>건물별 처리 전 신고</h3><div id="chartBuilding"></div></div> <!-- 건물별 막대그래프 -->
        <div class="t-card"><h3>유형별 처리 전 신고</h3><div id="chartCategory"></div></div> <!-- 유형별 막대그래프 -->
      </div> <!-- 그래프 두 개 끝 -->
      <div class="t-card"><h3>최근 30일 하루 접수 건수</h3><div id="chartDaily"></div></div> <!-- 날짜별 기둥 그래프 -->
      <div class="t-card"><h3>🚨 먼저 볼 신고 <small>긴급·높음, 처리 전, 오래된 순</small></h3><ul class="hot-list" id="hotList"></ul></div> <!-- 급한 신고 목록 -->
    </section> <!-- 대시보드 끝 -->

    <section class="t-tab" id="tab-list" hidden> <!-- 신고 관리 탭 내용 -->
      <div class="t-filters"> <!-- 거르기 도구 줄 -->
        <label><span>상태</span><select id="fStatus"> <!-- 상태 거르기 -->
          <option value="open">처리 전 (접수+처리중)</option><option value="">전체</option> <!-- 처리 전(기본), 전체 -->
          <option value="new">접수</option><option value="doing">처리중</option> <!-- 접수, 처리중 -->
          <option value="done">처리완료</option><option value="rejected">반려</option></select></label> <!-- 처리완료, 반려 -->
        <label><span>종류</span><select id="fKind"><option value="">전체</option><option value="danger">⚠️ 위험</option><option value="incon">🙁 불편</option></select></label> <!-- 종류 거르기 -->
        <label><span>위험도</span><select id="fSeverity"></select></label> <!-- 위험도 거르기 (파이썬이 채움) -->
        <label><span>건물</span><select id="fBuilding"></select></label> <!-- 건물 거르기 (파이썬이 채움) -->
        <label class="grow"><span>검색</span><input id="fSearch" placeholder="제목·장소·내용·신고자" /></label> <!-- 검색 칸 -->
        <button class="btn btn-quiet" id="btnCsv" type="button">⬇️ CSV (엑셀)</button> <!-- CSV 내려받기 버튼 -->
      </div> <!-- 거르기 도구 끝 -->
      <p class="t-count" id="listCount"></p> <!-- 몇 건인지 -->
      <div class="t-table-wrap"><table class="t-table" id="reportTable"></table></div> <!-- 신고 표 (파이썬이 채움) -->
    </section> <!-- 신고 관리 끝 -->

    <section class="t-tab" id="tab-map" hidden> <!-- 지도 탭 내용 -->
      <div class="t-maptools"> <!-- 지도 도구 줄 -->
        <select id="mBuilding"></select> <!-- 건물 고르기 -->
        <div class="floor-list" id="mFloors"></div> <!-- 층 버튼들 -->
        <label class="t-check"><input type="checkbox" id="mOnlyOpen" checked /> 처리 전만</label> <!-- 처리 전 신고만 보기 체크 -->
      </div> <!-- 지도 도구 끝 -->
      <div class="t-mapbox"><svg id="tmap" class="map" aria-label="신고 지도"></svg></div> <!-- 도면이 그려지는 곳 -->
      <p class="t-count">핀을 누르면 신고 내용이 열려요. 휠·두 손가락으로 확대, 끌어서 이동.</p> <!-- 사용 안내 -->
    </section> <!-- 지도 탭 끝 -->
  </main> <!-- 관리 화면 끝 -->

  <!-- 신고 상세 · 처리 -->
  <dialog class="sheet wide" id="detailDialog"> <!-- 신고 자세히 보기 + 처리 창 -->
    <header class="sheet-head"> <!-- 창 머리 -->
      <div id="dHead"></div> <!-- 종류·위험도·상태·제목 (파이썬이 채움) -->
      <button class="icon-btn" type="button" data-close aria-label="닫기"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button> <!-- X 닫기 버튼 -->
    </header> <!-- 창 머리 끝 -->
    <div class="sheet-body"> <!-- 창 몸통 -->
      <div class="t-detail"> <!-- 내용 + 작은 지도 -->
        <div id="dInfo"></div> <!-- 신고 내용·사진 (파이썬이 채움) -->
        <div><svg id="miniMap" class="map mini-map" aria-label="신고 위치"></svg><p class="t-count" id="miniCap"></p></div> <!-- 신고 위치 작은 지도 -->
      </div> <!-- 내용 + 지도 끝 -->
      <div class="t-actions"> <!-- 처리 도구들 -->
        <div> <!-- 첫째 칸: 상태 -->
          <h4>처리 상태</h4> <!-- 제목 -->
          <div class="seg" id="dStatus"></div> <!-- 상태 버튼들 (파이썬이 채움) -->
          <input id="dNote" class="t-input" maxlength="200" placeholder="메모 (선택) 예) 시설팀에 수리 요청함" /> <!-- 상태를 바꿀 때 남길 메모 -->
          <button class="btn btn-primary" id="dStatusSave" type="button" disabled>상태 저장</button> <!-- 상태 저장 버튼 -->
        </div> <!-- 첫째 칸 끝 -->
        <div> <!-- 둘째 칸: 담당자·메모 -->
          <h4>담당자</h4> <!-- 제목 -->
          <input id="dAssignee" class="t-input" maxlength="30" placeholder="예) 시설 담당 박OO 주무관" /> <!-- 담당자 칸 -->
          <button class="btn btn-quiet" id="dAssigneeSave" type="button">담당자 저장</button> <!-- 담당자 저장 버튼 -->
          <h4>처리 메모</h4> <!-- 제목 -->
          <textarea id="dMemo" class="t-input" rows="3" maxlength="1000" placeholder="진행 상황을 기록해 두세요"></textarea> <!-- 메모 칸 -->
          <button class="btn btn-quiet" id="dMemoSave" type="button">메모 추가</button> <!-- 메모 저장 버튼 -->
        </div> <!-- 둘째 칸 끝 -->
        <div> <!-- 셋째 칸: 기록·장난 신고·삭제 -->
          <h4>처리 기록</h4> <!-- 제목 -->
          <ul class="t-events" id="dEvents"></ul> <!-- 처리 기록 목록 (파이썬이 채움) -->
          <div class="t-abuse" id="dAbuse"></div> <!-- 장난 신고 막기 칸 (파이썬이 채움) -->
          <button class="btn-text-danger" id="dDelete" type="button">🗑️ 신고 삭제</button> <!-- 삭제 버튼 -->
        </div> <!-- 셋째 칸 끝 -->
      </div> <!-- 처리 도구 끝 -->
    </div> <!-- 창 몸통 끝 -->
  </dialog> <!-- 창 끝 -->

  <div class="toast" id="toast" role="status" aria-live="polite"></div> <!-- 화면 아래 잠깐 뜨는 알림 -->
'''  # 선생님 화면 틀 끝


def mount(page):  # 화면 틀을 페이지에 그리는 함수
    """로딩 문구만 남기고 화면 틀을 그린다."""  # 이 함수가 하는 일을 적은 설명글
    html, cls = (STUDENT, STUDENT_CLASS) if page == "student" else (TEACHER, TEACHER_CLASS)  # 학생용이면 학생 틀, 아니면 선생님 틀
    loading = document.getElementById("loading")  # 준비 화면 (지우지 않고 다시 붙이려고 잡아 둔다)
    document.body.innerHTML = html  # 페이지 내용을 화면 틀로 바꾼다
    if cls:  # 꾸미기 이름이 있으면
        document.body.className = cls  # <body> 에 붙인다
    if loading:  # 준비 화면이 있었으면
        document.body.appendChild(loading)  # 다시 붙인다 (파이썬 준비가 끝날 때까지 보이게)
