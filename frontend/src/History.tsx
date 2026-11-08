import { useEffect, useRef, useState } from "react";
import Chart from "chart.js/auto";
import { api, validIssues, dayKey, weekDates, type Entry } from "./api";
import s from "./ui.module.css";
export function History({
  aggregate,
  open,
  analyze,
}: {
  aggregate: boolean;
  open: (a: Entry) => void;
  analyze: () => void;
}) {
  const [rows, set] = useState<Entry[] | null>(null),
    [error, fail] = useState(""),
    [retry, reload] = useState(0);
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = new AbortController();
    fail("");
    api
      .records(c.signal)
      .then((r) => {
        if (!c.signal.aborted) set(r);
      })
      .catch((e) => {
        if (!c.signal.aborted) fail(e.message);
      });
    return () => c.abort();
  }, [retry]);
  const days = weekDates().map((date) => {
    const matches = (rows || []).filter(
      (a) => dayKey(new Date(a.savedAt)) === date,
    );
    const scores = matches.flatMap((a) => (a.score === null ? [] : [a.score]));
    return {
      date,
      count: matches.length,
      mean: scores.length
        ? Math.round(scores.reduce((x, y) => x + y, 0) / scores.length)
        : null,
    };
  });
  const any = !!rows?.length;
  useEffect(() => {
    if (!aggregate || !any || !canvas.current) return;
    const chart = new Chart(canvas.current, {
      type: "line",
      data: {
        labels: days.map((d) => d.date.slice(5)),
        datasets: [
          {
            data: days.map((d) => d.mean),
            borderColor: "#006b5b",
            pointRadius: 4,
            pointBackgroundColor: "#006b5b",
            spanGaps: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: { y: { min: 0, max: 100 } },
      },
    });
    return () => chart.destroy();
  }, [rows, aggregate]);
  const frequencies = new Map<string, number>();
  for (const row of rows || [])
    for (const word of new Set(
      validIssues(row).map((i) => row.sourceText.slice(i.start, i.end)),
    ))
      frequencies.set(word, (frequencies.get(word) || 0) + 1);
  const top = [...frequencies].sort((a, b) => b[1] - a[1])[0];
  const scores = days.filter((d) => d.mean !== null);
  const change =
    scores.length >= 2 ? scores.at(-1)!.mean! - scores[0].mean! : null;
  return (
    <>
      <h1>{aggregate ? "종합 분석" : "학습 기록"}</h1>
      {error ? (
        <p role="alert">
          {error} <button onClick={() => reload(retry + 1)}>다시 시도</button>
        </p>
      ) : !rows ? (
        <p role="status">기록을 불러오는 중이에요.</p>
      ) : !any ? (
        <p>아직 학습 기록이 없어요. 중앙의 연습 메뉴에서 시작해 보세요.</p>
      ) : !aggregate ? (
        <>
          <button className={s.primary} onClick={analyze}>
            학습 분석하기 <span>→</span>
          </button>
          <small>전체 {rows.length}회 · 최근 기록순</small>
          {rows.map((a) => (
            <button
              key={a.attemptId}
              className={s.recordRow}
              onClick={() => open(a)}
            >
              <b>{a.score === null ? "분석 불가" : a.score + "점"}</b>
              <span>
                <strong>{a.sourceText}</strong>
                <small>{new Date(a.savedAt).toLocaleString("ko-KR")}</small>
              </span>
              <span>›</span>
            </button>
          ))}
        </>
      ) : (
        <>
          <section className={s.hero}>
            <small>전체 학습 {rows.length}회</small>
            <h2>최근 7일 점수 추이</h2>
            <p>
              {change === null
                ? "비교할 날짜가 더 필요해요."
                : scores[0].date.slice(5) +
                  " 대비 " +
                  scores.at(-1)!.date.slice(5) +
                  " 평균이 " +
                  (change === 0
                    ? "같아요."
                    : Math.abs(change) +
                      "점 " +
                      (change > 0 ? "올랐어요." : "낮아졌어요."))}
            </p>
            <div className={s.chart}>
              <canvas
                ref={canvas}
                role="img"
                aria-label="최근 7일 평균 점수 추이. 아래 표에 날짜별 값이 있습니다."
              />
            </div>
          </section>
          <section className={s.card}>
            <h2>다시 연습할 구간</h2>
            <p>
              {top
                ? "‘" +
                  top[0] +
                  "’ 구간이 " +
                  top[1] +
                  "개 기록에 표시됐어요. 해당 글자가 들어간 예문을 다시 읽어 보세요."
                : "표시된 연습 구간이 없어요."}
            </p>
          </section>
          <table>
            <thead>
              <tr>
                <th>날짜</th>
                <th>횟수</th>
                <th>평균 점수</th>
              </tr>
            </thead>
            <tbody>
              {days.map((d) => (
                <tr key={d.date}>
                  <td>{d.date.slice(5)}</td>
                  <td>{d.count}회</td>
                  <td>{d.mean === null ? "점수 없음" : d.mean + "점"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </>
  );
}
