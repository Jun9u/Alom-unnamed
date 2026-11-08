import { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  api,
  demo,
  isMock,
  type Entry,
  type Scenario,
  type Sentence,
} from "./api";
import { History } from "./History";
import { Practice, Feedback, Microphone } from "./Practice";
import s from "./ui.module.css";
function Library({ pick }: { pick: (item: Sentence) => void }) {
  const [rows, set] = useState<Sentence[] | null>(null),
    [error, fail] = useState(""),
    [category, filter] = useState("전체"),
    [retry, reload] = useState(0);
  useEffect(() => {
    const ctl = new AbortController();
    set(null);
    fail("");
    api
      .sentences(ctl.signal)
      .then((r) => {
        if (!ctl.signal.aborted) set(r);
      })
      .catch((e) => {
        if (!ctl.signal.aborted) fail(e.message);
      });
    return () => ctl.abort();
  }, [retry]);
  const first = rows?.find((x) => x.category === "인사") || rows?.[0];
  return (
    <>
      <section className={s.hero}>
        <small>오늘의 연습</small>
        <h1>
          {first?.category === "인사" ? "반갑게 인사해요" : "목소리로 연습해요"}
        </h1>
        <p>목소리를 녹음하고 시각적 피드백으로 연습해 보세요.</p>
        {first && (
          <button className={s.primary} onClick={() => pick(first)}>
            {first.category} 연습 시작 <span>→</span>
          </button>
        )}
      </section>
      <h2>예문 둘러보기</h2>
      {error ? (
        <div role="alert">
          {error}{" "}
          <button onClick={() => reload((n) => n + 1)}>다시 시도</button>
        </div>
      ) : !rows ? (
        <p role="status">예문을 불러오는 중이에요.</p>
      ) : !rows.length ? (
        <p>등록된 예문이 없어요.</p>
      ) : (
        <>
          <div className={s.filters}>
            {["전체", ...new Set(rows.map((x) => x.category))].map((c) => (
              <button
                key={c}
                aria-pressed={c === category}
                onClick={() => filter(c)}
              >
                {c}
              </button>
            ))}
          </div>
          {rows
            .filter((x) => category === "전체" || x.category === category)
            .map((item) => (
              <button
                className={s.row}
                key={item.id}
                onClick={() => pick(item)}
              >
                <span>
                  <small>{item.category}</small>
                  {item.text}
                </span>
                <b aria-hidden="true">›</b>
              </button>
            ))}
        </>
      )}
    </>
  );
}
function Controls({ refresh }: { refresh: () => void }) {
  return (
    <details className={s.demo}>
      <summary>시연 설정</summary>
      <label>
        분석 시나리오
        <select
          aria-label="분석 시나리오"
          defaultValue={demo.scenario}
          onChange={(e) => {
            demo.scenario = e.target.value as Scenario;
          }}
        >
          {Object.entries({
            success: "성공",
            silence: "무음",
            noise: "잡음",
            different: "다른 문장",
            unavailable: "분석 불가",
            server: "서버 오류",
            network: "네트워크 오류",
            slow: "지연 후 성공",
          }).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </label>
      <label>
        예문 목록
        <select
          aria-label="예문 목록"
          defaultValue={demo.list}
          onChange={(e) => {
            demo.list = e.target.value;
            refresh();
          }}
        >
          <option value="normal">정상</option>
          <option value="empty">빈 목록</option>
          <option value="error">오류</option>
        </select>
      </label>
      <label>
        <input
          type="checkbox"
          defaultChecked={demo.emptyHistory}
          onChange={(e) => {
            demo.emptyHistory = e.target.checked;
            refresh();
          }}
        />{" "}
        빈 학습 기록
      </label>
    </details>
  );
}
function Today({
  item,
  onDone,
  onPending,
}: {
  onPending: (value: boolean) => void;
  item: Sentence | null;
  onDone: (a: Entry) => void;
}) {
  const [sentence, set] = useState(item),
    [error, fail] = useState(""),
    [retry, reload] = useState(0);
  useEffect(() => {
    if (item) return;
    const c = new AbortController();
    fail("");
    api
      .sentences(c.signal)
      .then((rows) => {
        if (c.signal.aborted) return;
        const today = rows.find((s) => s.id === "s2") || rows[0];
        if (today) set(today);
        else fail("등록된 예문이 없어요.");
      })
      .catch((e) => {
        if (!c.signal.aborted) fail(e.message);
      });
    return () => c.abort();
  }, [item, retry]);
  return sentence ? (
    <Practice onPending={onPending} item={sentence} onDone={onDone} />
  ) : (
    <p role="status">
      {error || "예문을 불러오는 중이에요."}
      {error && <button onClick={() => reload(retry + 1)}>다시 시도</button>}
    </p>
  );
}
function App() {
  const [item, pick] = useState<Sentence | null>(null),
    [page, setPage] = useState("home"),
    [selected, select] = useState<Entry | null>(null),
    [version, refresh] = useState(0);
  const [pending, setPending] = useState(false);
  const main = useRef<HTMLElement>(null);
  function go(to: string) {
    setPage(to);
    window.scrollTo(0, 0);
    requestAnimationFrame(() => main.current?.focus());
  }
  function detail(a: Entry) {
    select(a);
    go("detail");
  }
  function navigate(to: string) {
    if (page === to) return;
    if (
      page === "home" &&
      pending &&
      !window.confirm("이동하면 분석 전 녹음이 사라져요. 이동할까요?")
    )
      return;
    if (to === "home") pick(null);
    go(to);
  }
  return (
    <div className={s.shell}>
      <header>
        <strong>바르미</strong>
        <small>발음 연습</small>
      </header>
      <main ref={main} tabIndex={-1}>
        {page === "home" ? (
          <Today
            key={item?.id || "today"}
            item={item}
            onDone={detail}
            onPending={setPending}
          />
        ) : page === "library" ? (
          <Library
            key={version}
            pick={(s) => {
              pick(s);
              go("home");
            }}
          />
        ) : page === "history" || page === "aggregate" ? (
          <History
            key={version}
            aggregate={page === "aggregate"}
            open={detail}
            analyze={() => go("aggregate")}
          />
        ) : page === "detail" && selected ? (
          <>
            <h1>개별 분석</h1>
            <Feedback key={selected.attemptId} a={selected} />
            <button
              className={s.primary}
              onClick={() => {
                pick({
                  id: selected.sentenceId,
                  text: selected.sourceText,
                  category: "다시 연습",
                });
                go("home");
              }}
            >
              다시 연습
            </button>
            <button onClick={() => go("history")}>학습 기록 보기</button>
          </>
        ) : page === "advanced" ? (
          <>
            <h1>심화 학습</h1>
            {["긴 문장 읽기", "특정 발음 집중 연습"].map((title) => (
              <section className={s.card} key={title}>
                <small>준비 중</small>
                <h2>{title}</h2>
              </section>
            ))}
          </>
        ) : (
          <>
            <h1>설정</h1>
            {isMock && <Controls refresh={() => refresh((x) => x + 1)} />}
          </>
        )}
        {isMock && (
          <small>시연용 분석 결과 · 실제 발음 평가는 제공하지 않아요.</small>
        )}
      </main>
      <nav className={s.dock} aria-label="하단 메뉴">
        {[
          ["library", "예문"],
          ["history", "학습 기록"],
          ["home", "기본 연습"],
          ["advanced", "심화 학습"],
          ["settings", "설정"],
        ].map(([key, title]) => (
          <button
            key={key}
            className={key === "home" ? s.homeMic : undefined}
            aria-label={key === "home" ? "기본 연습으로 이동" : undefined}
            aria-current={
              page === key ||
              (key === "history" && ["aggregate", "detail"].includes(page))
                ? "page"
                : undefined
            }
            onClick={() => navigate(key)}
          >
            {key === "home" ? (
              <Microphone />
            ) : (
              <span aria-hidden="true">
                {
                  { library: "▤", history: "◷", advanced: "▥", settings: "⚙" }[
                    key
                  ]
                }
              </span>
            )}
            {key !== "home" && title}
          </button>
        ))}
      </nav>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
