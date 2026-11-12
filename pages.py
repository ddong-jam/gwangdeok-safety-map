"""화면 틀 (HTML). mount("student" | "teacher") 가 <body> 에 그린다."""
from js import document

STUDENT_CLASS = ''
STUDENT = '''
  <header class="topbar">
    <a class="brand" href="./">
      <span class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 32 32"><path d="M16 30c-1-4-10-9-10-17a10 10 0 0 1 20 0c0 8-9 13-10 17z" /><circle cx="16" cy="13" r="4" /></svg>
      </span>
      <span class="brand-text">
        <strong>광덕 안전지도</strong>
        <small>광덕중·고등학교 안전신문고</small>
      </span>
    </a>
    <div class="topbar-actions">
      <button id="btnReport" class="btn btn-danger" type="button" disabled>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
        <span>위험/불편 신고</span>
      </button>
    </div>
  </header>

  <main class="layout">
    <section class="stage" aria-label="평면도">
      <svg id="map" class="map" role="application" aria-label="확대·이동 가능한 평면도"></svg>
      <div class="stage-top">
        <nav class="crumbs" id="crumbs" aria-label="현재 위치"></nav>
        <div class="search" id="search">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4 4" /></svg>
          <input id="searchInput" type="search" placeholder="반·교실 찾기 (예: 2-1)" autocomplete="off" enterkeyhint="search"
                 aria-label="반이나 교실 이름으로 찾기" aria-controls="searchResults" />
          <ul class="search-results" id="searchResults" role="listbox" hidden></ul>
        </div>
      </div>
      <div class="floorbar" id="floorbar" role="tablist" aria-label="층 선택"></div>
      <div class="map-tools">
        <button class="tool" id="zoomIn" type="button" title="확대" aria-label="확대"><svg viewBox="0 0 24 24"><path d="M12 6v12M6 12h12" /></svg></button>
        <button class="tool" id="zoomOut" type="button" title="축소" aria-label="축소"><svg viewBox="0 0 24 24"><path d="M6 12h12" /></svg></button>
        <button class="tool" id="zoomFit" type="button" title="전체 보기" aria-label="전체 보기"><svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" /></svg></button>
      </div>
      <div class="mode-banner" id="modeBanner" hidden>
        <span class="pulse" aria-hidden="true"></span>
        <span id="modeText">도면에서 위험하거나 불편한 곳을 눌러 위치를 찍어주세요</span>
        <button class="btn btn-ghost-light" id="modeCancel" type="button">취소</button>
      </div>
    </section>

    <aside class="panel" id="panel">
      <section class="ctx" id="ctx"></section>
      <section class="reports">
        <div class="reports-head">
          <h2 id="listTitle">신고 현황</h2>
          <div class="stats" id="stats"></div>
        </div>
        <ul class="report-list" id="reportList"></ul>
        <p class="demo-note" id="demoNote" hidden>체험 모드예요. 신고가 이 브라우저에만 저장돼요.</p>
      </section>
    </aside>
  </main>

  <!-- 신고 작성 -->
  <dialog class="sheet" id="formDialog">
    <form id="reportForm" method="dialog">
      <header class="sheet-head">
        <div>
          <p class="eyebrow" id="formWhere">위치</p>
          <h2>위험/불편 신고</h2>
          <p class="who-line" id="formWho" hidden></p>
        </div>
        <button class="icon-btn" type="button" data-close aria-label="닫기"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
      </header>
      <div class="sheet-body">
        <fieldset><legend>무엇을 신고하나요?</legend>
          <div class="kinds" id="kindChips">
            <label class="kind-danger"><input type="radio" name="kind" value="danger" checked /><span><b>⚠️ 위험</b><small>다치거나 사고가 날 수 있어요</small></span></label>
            <label class="kind-incon"><input type="radio" name="kind" value="incon" /><span><b>🙁 불편</b><small>위험하진 않지만 불편해요</small></span></label>
          </div></fieldset>
        <fieldset><legend>어떤 문제인가요?</legend><div class="chips" id="catChips"></div></fieldset>
        <fieldset><legend id="sevLegend">얼마나 위험한가요?</legend><div class="sev" id="sevChips"></div></fieldset>
        <label class="field"><span>제목 <em>*</em></span>
          <input name="title" required maxlength="60" placeholder="예) 2층 계단 난간이 흔들려요 / 정수기가 고장났어요" /></label>
        <label class="field"><span>정확한 장소</span>
          <input name="spot" maxlength="60" placeholder="예) 2-3반 앞 복도, 계단실 2" /></label>
        <label class="field"><span>자세한 내용</span>
          <textarea name="desc" rows="4" maxlength="1000" placeholder="언제부터, 얼마나 위험하거나 불편한지 적어주세요"></textarea></label>
        <div class="field"><span>사진 (선택)</span>
          <label class="photo-drop">
            <input type="file" name="photo" accept="image/*" capture="environment" hidden />
            <img id="photoPreview" alt="" hidden />
            <span id="photoHint">사진 추가 · 촬영</span>
          </label>
        </div>
        <label class="field"><span>이름 (선택)</span>
          <input name="reporter" maxlength="30" placeholder="비워두면 익명으로 접수돼요" /></label>
        <div class="notice">
          <b>📢 신고 전에 꼭 읽어 주세요</b>
          <ul>
            <li>내가 직접 본 위험·불편만 사실대로 신고해요.</li>
            <li id="noticeRecord">신고하면 시간과 이 기기 정보가 함께 기록돼요. (익명이어도 기록돼요)</li>
            <li>장난·허위 신고는 선생님이 반려하고 이 기기의 신고를 막을 수 있으며, 학교 생활지도를 받을 수 있어요.</li>
            <li>급하게 다칠 것 같은 일은 신고하고 바로 가까운 선생님께도 말씀드려요.</li>
          </ul>
          <label class="check"><input type="checkbox" name="pledge" required /><span><b>사실대로 신고합니다</b></span></label>
        </div>
      </div>
      <footer class="sheet-foot">
        <button class="btn btn-quiet" type="button" data-close>취소</button>
        <button class="btn btn-danger" type="submit" id="formSubmit">신고 접수</button>
      </footer>
    </form>
  </dialog>

  <!-- 학생 로그인 (신고할 때만) -->
  <dialog class="sheet" id="loginDialog">
    <header class="sheet-head">
      <div>
        <p class="eyebrow">위험/불편 신고</p>
        <h2 id="loginTitle">구글 계정으로 로그인</h2>
      </div>
      <button class="icon-btn" type="button" data-close aria-label="닫기"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
    </header>
    <div class="sheet-body">
      <p class="login-lead">장난 신고를 막으려고 <b>신고할 때만</b> 로그인해요. 지도와 다른 신고 보기는 로그인 없이 돼요.</p>
      <ul class="login-points">
        <li>누가 신고했는지는 <b>선생님만</b> 볼 수 있어요. 다른 학생에게는 보이지 않아요.</li>
        <li>이 기기에서는 30일 동안 로그인이 유지돼요. 함께 쓰는 컴퓨터라면 신고 뒤 꼭 로그아웃해요.</li>
        <li id="loginDomain" hidden></li>
      </ul>
      <label class="field" id="demoNameField" hidden><span>이름 (체험 모드)</span>
        <input id="demoName" maxlength="30" placeholder="체험 모드라 구글 대신 이름만 넣어요" /></label>
      <button class="btn btn-google" id="btnGoogle" type="button">
        <svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.5l6.7-6.7C35.6 2.4 30.2 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.8 6C12.4 13.6 17.7 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.6 5.9c4.4-4.1 7-10.1 7-17.6z"/><path fill="#FBBC05" d="M10.5 28.7c-.5-1.4-.8-3-.8-4.7s.3-3.3.8-4.7l-7.8-6C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7l7.8-6z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.6-5.9c-2.1 1.4-4.9 2.3-8.3 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.8 6C6.6 42.6 14.6 48 24 48z"/></svg>
        <span>Google 계정으로 로그인</span>
      </button>
    </div>
  </dialog>

  <!-- 신고 보기 -->
  <dialog class="sheet" id="detailDialog"><div id="detailBody"></div></dialog>

  <div class="toast" id="toast" role="status" aria-live="polite"></div>
'''

TEACHER_CLASS = 'teacher'
TEACHER = '''
  <header class="topbar">
    <a class="brand" href="./teacher.html">
      <span class="brand-mark t-mark" aria-hidden="true">🛡️</span>
      <span class="brand-text">
        <strong>선생님 관리</strong>
        <small>광덕 안전지도 · 신고 관리</small>
      </span>
    </a>
    <div class="topbar-actions">
      <span class="who" id="who"></span>
      <button class="btn btn-quiet" id="btnLogout" type="button" hidden>로그아웃</button>
    </div>
  </header>

  <!-- 로그인 -->
  <section class="t-login" id="login" hidden>
    <form class="t-card" id="loginForm" method="dialog">
      <h1>로그인</h1>
      <p class="sub" id="loginNote"></p>
      <label class="field"><span>이름</span><input name="name" maxlength="30" required placeholder="처리 기록에 남을 이름 (예: 김안전 선생님)" /></label>
      <div id="loginShared" hidden>
        <label class="field"><span>이메일</span><input name="email" type="email" autocomplete="username" /></label>
        <label class="field"><span>비밀번호</span><input name="password" type="password" autocomplete="current-password" /></label>
      </div>
      <label class="check"><input type="checkbox" name="keep" /><span><b>이 기기에서 로그인 유지 (14일)</b><small>내 업무용 컴퓨터에서만 체크하세요. 여러 사람이 쓰는 컴퓨터에서는 체크하지 마세요.</small></span></label>
      <p class="t-error" id="loginError" hidden></p>
      <button class="btn btn-primary" type="submit">들어가기</button>
    </form>
  </section>

  <!-- 관리 화면 -->
  <main class="t-main" id="app" hidden>
    <nav class="t-tabs" role="tablist">
      <button role="tab" data-tab="dash" aria-selected="true">📊 대시보드</button>
      <button role="tab" data-tab="list" aria-selected="false">📋 신고 관리</button>
      <button role="tab" data-tab="map" aria-selected="false">🗺️ 지도로 보기</button>
    </nav>
    <p class="demo-note" id="demoNote" hidden>체험 모드예요. 이 브라우저에서 접수한 신고만 보여요. (README 의 "신고를 모두 함께 보기"를 설정하면 모든 학생의 신고가 모여요)</p>

    <section class="t-tab" id="tab-dash">
      <div class="tiles" id="tiles"></div>
      <div class="t-grid2">
        <div class="t-card"><h3>건물별 처리 전 신고</h3><div id="chartBuilding"></div></div>
        <div class="t-card"><h3>유형별 처리 전 신고</h3><div id="chartCategory"></div></div>
      </div>
      <div class="t-card"><h3>최근 30일 하루 접수 건수</h3><div id="chartDaily"></div></div>
      <div class="t-card"><h3>🚨 먼저 볼 신고 <small>긴급·높음, 처리 전, 오래된 순</small></h3><ul class="hot-list" id="hotList"></ul></div>
    </section>

    <section class="t-tab" id="tab-list" hidden>
      <div class="t-filters">
        <label><span>상태</span><select id="fStatus">
          <option value="open">처리 전 (접수+처리중)</option><option value="">전체</option>
          <option value="new">접수</option><option value="doing">처리중</option>
          <option value="done">처리완료</option><option value="rejected">반려</option></select></label>
        <label><span>종류</span><select id="fKind"><option value="">전체</option><option value="danger">⚠️ 위험</option><option value="incon">🙁 불편</option></select></label>
        <label><span>위험도</span><select id="fSeverity"></select></label>
        <label><span>건물</span><select id="fBuilding"></select></label>
        <label class="grow"><span>검색</span><input id="fSearch" placeholder="제목·장소·내용·신고자" /></label>
        <button class="btn btn-quiet" id="btnCsv" type="button">⬇️ CSV (엑셀)</button>
      </div>
      <p class="t-count" id="listCount"></p>
      <div class="t-table-wrap"><table class="t-table" id="reportTable"></table></div>
    </section>

    <section class="t-tab" id="tab-map" hidden>
      <div class="t-maptools">
        <select id="mBuilding"></select>
        <div class="floor-list" id="mFloors"></div>
        <label class="t-check"><input type="checkbox" id="mOnlyOpen" checked /> 처리 전만</label>
      </div>
      <div class="t-mapbox"><svg id="tmap" class="map" aria-label="신고 지도"></svg></div>
      <p class="t-count">핀을 누르면 신고 내용이 열려요. 휠·두 손가락으로 확대, 끌어서 이동.</p>
    </section>
  </main>

  <!-- 신고 상세 · 처리 -->
  <dialog class="sheet wide" id="detailDialog">
    <header class="sheet-head">
      <div id="dHead"></div>
      <button class="icon-btn" type="button" data-close aria-label="닫기"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
    </header>
    <div class="sheet-body">
      <div class="t-detail">
        <div id="dInfo"></div>
        <div><svg id="miniMap" class="map mini-map" aria-label="신고 위치"></svg><p class="t-count" id="miniCap"></p></div>
      </div>
      <div class="t-actions">
        <div>
          <h4>처리 상태</h4>
          <div class="seg" id="dStatus"></div>
          <input id="dNote" class="t-input" maxlength="200" placeholder="메모 (선택) 예) 시설팀에 수리 요청함" />
          <button class="btn btn-primary" id="dStatusSave" type="button" disabled>상태 저장</button>
        </div>
        <div>
          <h4>담당자</h4>
          <input id="dAssignee" class="t-input" maxlength="30" placeholder="예) 시설 담당 박OO 주무관" />
          <button class="btn btn-quiet" id="dAssigneeSave" type="button">담당자 저장</button>
          <h4>처리 메모</h4>
          <textarea id="dMemo" class="t-input" rows="3" maxlength="1000" placeholder="진행 상황을 기록해 두세요"></textarea>
          <button class="btn btn-quiet" id="dMemoSave" type="button">메모 추가</button>
        </div>
        <div>
          <h4>처리 기록</h4>
          <ul class="t-events" id="dEvents"></ul>
          <div class="t-abuse" id="dAbuse"></div>
          <button class="btn-text-danger" id="dDelete" type="button">🗑️ 신고 삭제</button>
        </div>
      </div>
    </div>
  </dialog>

  <div class="toast" id="toast" role="status" aria-live="polite"></div>
'''


def mount(page):
    """로딩 문구만 남기고 화면 틀을 그린다."""
    html, cls = (STUDENT, STUDENT_CLASS) if page == "student" else (TEACHER, TEACHER_CLASS)
    loading = document.getElementById("loading")
    document.body.innerHTML = html
    if cls:
        document.body.className = cls
    if loading:
        document.body.appendChild(loading)
