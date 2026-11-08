import { RecordingPlayer, sessionClips } from "./RecordingPlayer";
import { useEffect, useRef, useState } from "react";
import {
  api,
  delay,
  isMock,
  validIssues,
  type Entry,
  type Sentence,
} from "./api";
import { capture, micMessage } from "./record";
import s from "./ui.module.css";
const labels = {
  idle: "녹음 대기",
  permission: "권한 요청",
  recording: "녹음 중",
  ready: "녹음 확인",
  upload: "업로드 중",
  analysis: "분석 중",
  done: "완료",
  error: "오류",
};
type Phase = keyof typeof labels;
export function Feedback({ a }: { a: Entry }) {
  const issues = validIssues(a);
  let cursor = 0;
  return (
    <section className={s.card}>
      <small>목표 문장</small>
      <h2>{a.sourceText}</h2>
      <div className={s.trace}>
        <small>
          {a.attemptId.startsWith("example-")
            ? "시연용 파형 예시"
            : "녹음 입력 크기"}
        </small>
        <div className={s.bars} aria-label="녹음 입력 크기 요약">
          {a.levels?.length
            ? a.levels.map((v, i) => (
                <i key={i} style={{ height: Math.max(2, v * 66) + "px" }} />
              ))
            : "파형 정보 없음"}
        </div>
      </div>
      <RecordingPlayer key={a.attemptId} id={a.attemptId} />
      <small>{new Date(a.savedAt).toLocaleString("ko-KR")}</small>
      <small>{isMock ? "시연용 분석 결과" : "분석 결과"}</small>
      <h2>{a.score === null ? "분석 불가" : a.score + "점"}</h2>
      <p>{a.message}</p>
      <p className={s.quote}>
        {issues.map((i) => {
          const before = a.sourceText.slice(cursor, i.start);
          cursor = i.end;
          return (
            <span key={i.start}>
              {before}
              <mark>{a.sourceText.slice(i.start, i.end)}</mark>
            </span>
          );
        })}
        {a.sourceText.slice(cursor)}
      </p>
      {issues.map((i) => (
        <p key={i.start}>
          <strong>연습 구간 · {a.sourceText.slice(i.start, i.end)}</strong>
          <br />
          {i.description}
        </p>
      ))}
    </section>
  );
}
export function Practice({
  item,
  onDone,
  onPending,
}: {
  onPending: (value: boolean) => void;
  item: Sentence;
  onDone: (a: Entry) => void;
}) {
  const [phase, set] = useState<Phase>("idle"),
    [seconds, tick] = useState(0),
    [error, fail] = useState(""),
    [blob, save] = useState<Blob | null>(null),
    [url, setUrl] = useState("");
  const duration = useRef(0);
  useEffect(() => {
    const pending = phase === "permission" || phase === "recording" || !!blob;
    onPending(pending);
    if (!pending) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => {
      onPending(false);
      window.removeEventListener("beforeunload", warn);
    };
  }, [phase, blob, onPending]);
  const levels = useRef<number[]>([]);
  const active = useRef<AbortController | null>(null),
    stop = useRef<(() => void) | null>(null),
    canvas = useRef<HTMLCanvasElement>(null),
    started = useRef(0);
  useEffect(() => () => active.current?.abort(), []);
  useEffect(() => {
    if (!blob) {
      setUrl("");
      return;
    }
    const u = URL.createObjectURL(blob);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [blob]);
  useEffect(() => {
    if (phase !== "recording") return;
    const t = setInterval(
      () =>
        tick(
          Math.min(
            60,
            Math.floor((performance.now() - started.current) / 1000),
          ),
        ),
      200,
    );
    return () => clearInterval(t);
  }, [phase]);
  async function record() {
    if (
      active.current &&
      !active.current.signal.aborted &&
      ["permission", "recording", "analysis", "upload"].includes(phase)
    )
      return;
    active.current?.abort();
    const ctl = new AbortController();
    active.current = ctl;
    save(null);
    fail("");
    tick(0);
    set("permission");
    try {
      const end = await capture(
        canvas.current!,
        ctl.signal,
        (b, values) => {
          duration.current = (performance.now() - started.current) / 1000;
          levels.current = values;
          tick(
            Math.min(
              60,
              Math.round((performance.now() - started.current) / 1000),
            ),
          );
          save(b);
          set("ready");
        },
        (m) => {
          fail(m);
          set("error");
        },
      );
      if (!ctl.signal.aborted) {
        stop.current = end;
        started.current = performance.now();
        set("recording");
      }
    } catch (e) {
      if (!ctl.signal.aborted) {
        fail(micMessage(e));
        set("error");
      }
    }
  }
  const submitting = useRef(false);
  async function analyze() {
    if (!blob || submitting.current) return;
    submitting.current = true;
    active.current?.abort();
    const ctl = new AbortController();
    active.current = ctl;
    set("upload");
    fail("");
    try {
      let a = await api.submit(item, blob, ctl.signal, levels.current);
      const id = a.attemptId;
      const deadline = Date.now() + 90000;
      while (a.status === "processing") {
        set("analysis");
        await delay(500, ctl.signal);
        if (Date.now() > deadline)
          throw Error("분석 대기 시간이 지났어요. 다시 요청해 주세요.");
        a = await api.status(id, ctl.signal);
      }
      ctl.signal.throwIfAborted();
      if (a.sentenceId !== item.id || a.attemptId !== id)
        throw Error("요청과 결과가 일치하지 않아요.");
      sessionClips.set(id, { blob, duration: duration.current });
      onDone({
        ...a,
        levels: levels.current,
        savedAt: (a as Entry).savedAt || new Date().toISOString(),
      });
      set("done");
    } catch (e) {
      if (!ctl.signal.aborted) {
        fail(e instanceof Error ? e.message : "분석 요청에 실패했어요.");
        set("error");
      }
    } finally {
      submitting.current = false;
    }
  }
  const busy = ["permission", "upload", "analysis"].includes(phase);
  return (
    <>
      <h1>오늘의 연습</h1>
      <section className={s.studio}>
        <div className={s.signal}>
          {phase === "idle" && (
            <svg
              className={s.idleWave}
              aria-hidden="true"
              viewBox="0 0 300 50"
              preserveAspectRatio="none"
            >
              <path
                d="M0 25h16l3 -4 3 9 4 -19 4 31 4 -36 4 27 3 -11 4 6 5 -4 5 1h65 m56 0h32l3 -4 4 10 4 -16 4 24 4 -34 4 28 4 -10 5 5 6 -3h38"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
              />
            </svg>
          )}
          <canvas
            ref={canvas}
            width="650"
            height="88"
            aria-label="마이크 입력 파형"
          />
          <button
            className={s.mic}
            aria-label={phase === "recording" ? "녹음 종료" : "녹음 시작"}
            disabled={busy}
            onClick={phase === "recording" ? () => stop.current?.() : record}
          >
            {phase === "recording" ? "■" : <Microphone />}
          </button>
        </div>
        <strong role="status">
          {phase === "idle" ? "눌러서 녹음 시작" : labels[phase]}
        </strong>
        <small>
          {phase === "recording"
            ? seconds + "초 / 60초"
            : phase === "permission"
              ? "브라우저의 마이크 권한을 허용해 주세요."
              : "최대 60초 · 조용한 곳에서 읽어 주세요."}
        </small>
      </section>
      <section className={s.card}>
        <small>오늘의 예문 · {item.category}</small>
        <h2 className={s.quote}>{item.text}</h2>
      </section>
      {blob && url && <audio controls src={url} aria-label="내 녹음 듣기" />}
      {error && (
        <p role="alert" className={s.error}>
          {error}
        </p>
      )}

      {blob && phase !== "done" && (
        <button className={s.primary} disabled={busy} onClick={analyze}>
          {busy
            ? labels[phase]
            : phase === "error"
              ? "분석 다시 요청"
              : "분석 요청"}
        </button>
      )}
    </>
  );
}

export function Microphone() {
  return (
    <svg
      aria-hidden="true"
      width="36"
      height="36"
      viewBox="0 0 32 32"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
    >
      <rect x="12" y="3" width="8" height="16" rx="4" />
      <path d="M8 14v2a8 8 0 0 0 16 0v-2M16 24v5m-5 0h10" />
    </svg>
  );
}
