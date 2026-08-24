import { useEffect, useRef } from "react";
import { createFridayWorld } from "../scene/fridayWorld";

interface FridayCoreProps {
  status: string;
  line: string;
}

const HEAD: Record<string, [string, string]> = {
  idle: ["I keep watch.", "Say Friday."],
  listening: ["I am listening.", "Go ahead."],
  thinking: ["Give me a moment.", "Working it out."],
  speaking: ["Here is what I have.", ""],
  error: ["Signal lost.", "I will recover."],
};

export function FridayCore({ status, line }: FridayCoreProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const statusRef = useRef(status);
  statusRef.current = status;
  const worldRef = useRef<ReturnType<typeof createFridayWorld> | null>(null);
  const copy = HEAD[status] || HEAD.idle;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const world = createFridayWorld(canvas);
    worldRef.current = world;
    world.setStatus(statusRef.current);
    return () => {
      world.dispose();
      worldRef.current = null;
    };
  }, []);

  useEffect(() => {
    worldRef.current?.setStatus(status);
  }, [status]);

  return (
    <div className={`friday-core status-${status}`}>
      <canvas ref={canvasRef} />
      <div className="friday-core-copy">
        <h1>
          {copy[0]}
          {copy[1] ? (
            <>
              <br />
              {copy[1]}
            </>
          ) : null}
        </h1>
        {line ? <p className="friday-line">{line}</p> : null}
      </div>
    </div>
  );
}
