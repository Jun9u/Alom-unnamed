// Each capture owns its resources. A cancelled permission prompt may still resolve later.
export async function capture(
  canvas: HTMLCanvasElement,
  signal: AbortSignal,
  onFinish: (blob: Blob, levels: number[]) => void,
  onError: (message: string) => void,
) {
  if (
    !navigator.mediaDevices?.getUserMedia ||
    !window.MediaRecorder ||
    !window.AudioContext
  )
    throw Error(
      "이 브라우저에서 녹음을 사용할 수 없어요. HTTPS 또는 localhost에서 열어 주세요.",
    );
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  let ctx: AudioContext | undefined,
    recorder: MediaRecorder | undefined,
    frame = 0,
    timer = 0;
  function clean() {
    clearTimeout(timer);
    cancelAnimationFrame(frame);
    signal.removeEventListener("abort", cancel);
    stream.getTracks().forEach((t) => t.stop());
    if (ctx && ctx.state !== "closed") void ctx.close().catch(() => {});
  }
  function cancel() {
    if (recorder?.state === "recording") recorder.stop();
    clean();
  }
  try {
    signal.throwIfAborted();
    signal.addEventListener("abort", cancel, { once: true });
    ctx = new AudioContext();
    await ctx.resume();
    signal.throwIfAborted();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    ctx.createMediaStreamSource(stream).connect(analyser);
    const mimeType = [
      "audio/webm;codecs=opus",
      "audio/mp4",
      "audio/ogg;codecs=opus",
    ].find((t) => MediaRecorder.isTypeSupported(t));
    recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const samples: number[] = [];
    const rec = recorder,
      chunks: Blob[] = [];
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    let failed = false;
    rec.onerror = () => {
      failed = true;
      clean();
      if (!signal.aborted) onError("녹음 장치 연결을 확인해 주세요.");
    };
    rec.onstop = () => {
      clean();
      if (!signal.aborted && !failed) {
        if (chunks.length) {
          const count = Math.min(samples.length, 64);
          onFinish(
            new Blob(chunks, { type: chunks[0].type || rec.mimeType }),
            Array.from({ length: count }, (_, i) =>
              Math.max(
                ...samples.slice(
                  Math.floor((i * samples.length) / count),
                  Math.floor(((i + 1) * samples.length) / count),
                ),
              ),
            ),
          );
        } else onError("녹음 파일이 비어 있어요. 다시 녹음해 주세요.");
      }
    };
    stream.getAudioTracks()[0].onended = () => {
      if (rec.state === "recording") rec.stop();
    };
    const bytes = new Uint8Array(analyser.fftSize),
      g = canvas.getContext("2d");
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let last = 0;
    function draw(time: number) {
      if (!g) return;
      if (time - last > (reduced ? 180 : 25)) {
        last = time;
        analyser.getByteTimeDomainData(bytes);
        samples.push(
          bytes.reduce((max, v) => Math.max(max, Math.abs(v - 128) / 128), 0),
        );
        const w = canvas.width,
          h = canvas.height;
        g.clearRect(0, 0, w, h);
        g.strokeStyle = "#006b5b";
        g.lineWidth = 2;
        g.beginPath();
        bytes.forEach((v, i) => {
          const x = (i * w) / (bytes.length - 1),
            y = (v * h) / 256;
          i ? g.lineTo(x, y) : g.moveTo(x, y);
        });
        g.stroke();
      }
      frame = requestAnimationFrame(draw);
    }
    rec.start(250);
    frame = requestAnimationFrame(draw);
    const stop = () => {
      if (rec.state === "recording") rec.stop();
    };
    timer = window.setTimeout(stop, 60000);
    return stop;
  } catch (e) {
    cancel();
    throw e;
  }
}
export function micMessage(e: unknown) {
  if (e instanceof DOMException) {
    if (["NotAllowedError", "SecurityError"].includes(e.name))
      return "마이크 권한이 차단됐어요. 주소창의 사이트 설정에서 마이크를 허용한 뒤 다시 시도해 주세요.";
    if (e.name === "NotFoundError")
      return "마이크를 찾을 수 없어요. 장치를 연결해 주세요.";
    if (e.name === "NotReadableError")
      return "마이크가 사용 중이에요. 다른 앱의 녹음을 종료해 주세요.";
    if (e.name === "NotSupportedError")
      return "이 브라우저에서 지원하는 녹음 형식이 없어요.";
  }
  return e instanceof Error ? e.message : "녹음을 시작하지 못했어요.";
}
