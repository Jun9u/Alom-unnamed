export type Sentence = { id: string; text: string; category: string };
export type Issue = { start: number; end: number; description: string };
export type Attempt = {
  attemptId: string;
  sentenceId: string;
  sourceText: string;
  status: "processing" | "completed" | "failed";
  score: number | null;
  issues: Issue[];
  errorCode: string | null;
  message: string;
};
export type Entry = Attempt & { savedAt: string; levels?: number[] };
export type Day = { date: string; count: number; mean: number | null };
export interface Api {
  sentences(signal: AbortSignal): Promise<Sentence[]>;
  submit(
    sentence: Sentence,
    file: Blob,
    signal: AbortSignal,
    levels?: number[],
  ): Promise<Attempt>;
  status(id: string, signal: AbortSignal): Promise<Attempt>;
  records(signal: AbortSignal): Promise<Entry[]>;
}
export type Scenario =
  | "success"
  | "silence"
  | "noise"
  | "different"
  | "unavailable"
  | "server"
  | "network"
  | "slow";
export const demo = {
  scenario: "success" as Scenario,
  list: "normal",
  emptyHistory: false,
};
export const isMock = !import.meta.env.VITE_API_BASE_URL;
export function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    signal.throwIfAborted();
    const abort = () => {
      clearTimeout(timer);
      reject(signal.reason);
    };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, ms);
    signal.addEventListener("abort", abort, { once: true });
  });
}
export function validIssues(a: Attempt): Issue[] {
  const boundaries = new Set([0, a.sourceText.length]);
  for (const g of new Intl.Segmenter("ko", { granularity: "grapheme" }).segment(
    a.sourceText,
  ))
    boundaries.add(g.index);
  let last = 0;
  return [...a.issues]
    .sort((x, y) => x.start - y.start)
    .filter((i) => {
      if (
        !boundaries.has(i.start) ||
        !boundaries.has(i.end) ||
        i.end <= i.start ||
        i.start < last
      )
        return false;
      last = i.end;
      return true;
    });
}
const library: Sentence[] = [
  ["s1", "안녕하세요.", "인사"],
  ["s2", "만나서 반가워요.", "인사"],
  ["s3", "오늘 날씨가 좋네요.", "일상 대화"],
  ["s4", "주말에 산책하러 갈까요?", "일상 대화"],
  ["s5", "물을 한 잔 주시겠어요?", "부탁"],
  ["s6", "조금만 천천히 말씀해 주세요.", "부탁"],
].map(([id, text, category]) => ({ id, text, category }));
export function dayKey(d: Date) {
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}
export function weekDates() {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - 6 + i);
    return dayKey(d);
  });
}
const archiveKey = "malgyeol.attempts.v2";
function examples(): Entry[] {
  return [1, 2, 1, 0].map((sentenceIndex, i) => {
    const sentence = library[sentenceIndex];
    return {
      attemptId: "example-" + i,
      sentenceId: sentence.id,
      sourceText: sentence.text,
      status: "completed",
      score: [84, 80, 76, 72][i],
      errorCode: null,
      message: "표시된 구간을 천천히 이어 읽어 보세요.",
      issues: [
        {
          start: 0,
          end: 2,
          description: "첫 두 글자를 천천히 이어 읽어 보세요.",
        },
      ],
      savedAt: weekDates()[6 - i] + "T09:00:00",
      levels: [
        0.12, 0.36, 0.72, 0.41, 0.2, 0.16, 0.46, 0.84, 0.5, 0.25, 0.34, 0.6,
        0.44, 0.16,
      ],
    };
  });
}
function archived(): Entry[] {
  const raw = localStorage.getItem(archiveKey);
  if (raw) return JSON.parse(raw);
  const initial = examples();
  localStorage.setItem(archiveKey, JSON.stringify(initial));
  return initial;
}
const pending = new Map<
  string,
  { result: Attempt; scenario: Scenario; levels: number[] }
>();
const reasons = {
  silence: "녹음에서 목소리를 찾지 못했어요.",
  noise: "주변 소음이 커서 구간을 구분하기 어려워요.",
  different: "선택한 예문과 녹음한 문장이 달라요.",
  unavailable: "분석할 수 있는 구간이 부족해요.",
};
const mock: Api = {
  async sentences(signal) {
    await delay(300, signal);
    if (demo.list === "error") throw Error("예문을 불러오지 못했어요.");
    return demo.list === "empty" ? [] : library;
  },
  async submit(s, _file, signal, levels = []) {
    const scenario = demo.scenario;
    await delay(450, signal);
    if (scenario === "network")
      throw Error("네트워크 연결을 확인한 뒤 다시 시도해 주세요.");
    const attempt: Attempt = {
      attemptId: crypto.randomUUID(),
      sentenceId: s.id,
      sourceText: s.text,
      status: "processing",
      issues: [],
      score: null,
      errorCode: null,
      message: "분석 중이에요.",
    };
    pending.set(attempt.attemptId, {
      result: attempt,
      scenario,
      levels,
    });
    return attempt;
  },
  async status(id, signal) {
    const entry = pending.get(id);
    if (!entry) {
      const saved = archived().find((a) => a.attemptId === id);
      if (saved) return saved;
    }
    if (!entry) throw Error("연습 요청을 찾지 못했어요.");
    const { scenario, result } = entry;
    await delay(scenario === "slow" ? 6500 : 800, signal);
    if (scenario === "server")
      throw Error("분석 서버에서 오류가 발생했어요. 다시 요청해 주세요.");
    const reason = reasons[scenario as keyof typeof reasons];
    const done: Attempt = {
      ...result,
      status: reason ? "failed" : "completed",
      score: reason ? null : 84,
      errorCode: reason ? scenario : null,
      message: reason || "표시된 구간을 천천히 이어 읽어 보세요.",
      issues: reason
        ? []
        : [
            {
              start: 0,
              end: 2,
              description: "첫 두 글자를 천천히 이어 읽어 보세요.",
            },
          ],
    };
    const saved: Entry = {
      ...done,
      savedAt: new Date().toISOString(),
      levels: entry.levels,
    };
    const previous = archived();
    const existing = previous.find((a) => a.attemptId === id);
    if (existing) return existing;
    localStorage.setItem(archiveKey, JSON.stringify([saved, ...previous]));
    pending.delete(id);
    return saved;
  },
  async records(signal) {
    await delay(180, signal);
    return demo.emptyHistory
      ? []
      : archived().sort(
          (a, b) => Date.parse(b.savedAt) - Date.parse(a.savedAt),
        );
  },
};
const base = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
async function request<T>(
  path: string,
  signal: AbortSignal,
  body?: FormData,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(base + path, {
      signal,
      method: body ? "POST" : "GET",
      body,
      credentials: "include",
    });
  } catch (e) {
    signal.throwIfAborted();
    throw Error("네트워크 연결을 확인해 주세요.", { cause: e });
  }
  if (!response.ok)
    throw Error("서버가 요청을 처리하지 못했어요. (" + response.status + ")");
  return response.json();
}
const live: Api = {
  sentences: (s) => request("/sentences", s),
  records: (s) => request("/learning-records", s),
  status: (id, s) => request("/attempts/" + encodeURIComponent(id), s),
  submit: (sentence, file, s) => {
    const form = new FormData();
    form.append("sentenceId", sentence.id);
    const ext: Record<string, string> = {
      "audio/webm": "webm",
      "audio/mp4": "mp4",
      "audio/ogg": "ogg",
      "audio/wav": "wav",
    };
    form.append(
      "file",
      file,
      "recording." + (ext[file.type.split(";")[0]] || "bin"),
    );
    return request("/attempts", s, form);
  },
};
export const api: Api = isMock ? mock : live;
