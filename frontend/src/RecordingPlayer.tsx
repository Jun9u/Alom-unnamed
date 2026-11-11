import { useEffect, useRef, useState } from "react";
import s from "./ui.module.css";
type Clip = { blob: Blob; duration: number };
export const sessionClips = new Map<string, Clip>();
function clock(n: number) {
  const time = Math.floor(n);
  return Math.floor(time / 60) + ":" + String(time % 60).padStart(2, "0");
}
export function RecordingPlayer({ id }: { id: string }) {
  const clip = sessionClips.get(id),
    audio = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false),
    [time, setTime] = useState(0),
    [length, setLength] = useState(clip?.duration ?? 0),
    [failed, fail] = useState(false);
  useEffect(() => {
    if (!clip) return;
    const url = URL.createObjectURL(clip.blob);
    const player = new Audio(url);
    audio.current = player;
    player.onplay = () => setPlaying(true);
    player.onpause = () => setPlaying(false);
    player.ontimeupdate = () => setTime(player.currentTime);
    player.ondurationchange = () => {
      if (Number.isFinite(player.duration)) setLength(player.duration);
    };
    player.onended = () => {
      setPlaying(false);
      setTime(player.currentTime);
    };
    player.onerror = () => {
      fail(true);
      setPlaying(false);
    };
    return () => {
      player.onplay =
        player.onpause =
        player.onended =
        player.ontimeupdate =
        player.onerror =
        player.ondurationchange =
          null;
      player.pause();
      player.removeAttribute("src");
      player.load();
      URL.revokeObjectURL(url);
      audio.current = null;
    };
  }, [clip]);
  async function toggle() {
    const player = audio.current;
    if (!player) return;
    if (!player.paused) {
      player.pause();
      return;
    }
    if (player.ended) player.currentTime = 0;
    try {
      await player.play();
    } catch {
      if (audio.current === player) fail(true);
    }
  }
  return (
    <div className={s.player}>
      <button
        aria-pressed={playing}
        disabled={!clip || failed}
        onClick={toggle}
      >
        {playing ? "Ⅱ 일시정지" : "▶ 내 녹음 듣기"}
      </button>
      <small>
        {!clip
          ? "저장된 녹음이 없어요"
          : failed
            ? "녹음을 재생할 수 없어요"
            : clock(time) + " / " + clock(length)}
      </small>
    </div>
  );
}
