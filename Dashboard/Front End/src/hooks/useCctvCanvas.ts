import { useEffect } from 'react';
import { ICameraDevice } from '../types/soc.ts';

export function useCctvCanvas(
  canvasRef: React.RefObject<HTMLCanvasElement | null>,
  camera: ICameraDevice
) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number | undefined;

    const render = () => {
      const parent = canvas.parentElement;
      const width = (canvas.width = parent?.clientWidth || 320);
      const height = (canvas.height = parent?.clientHeight || 200);

      ctx.clearRect(0, 0, width, height);

      // 1. Nền đen CCTV sâu
      ctx.fillStyle = '#080B10';
      ctx.fillRect(0, 0, width, height);

      // Lưới phối cảnh hành lang
      ctx.strokeStyle = '#121822';
      ctx.lineWidth = 1;
      for (let x = 0; x < width; x += 32) {
        ctx.beginPath();
        ctx.moveTo(x, height);
        ctx.lineTo(width / 2 + (x - width / 2) * 0.35, height * 0.38);
        ctx.stroke();
      }
      for (let y = height * 0.38; y < height; y += 22) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Khung cửa hành lang hoặc vật thể nền
      ctx.fillStyle = '#0F151E';
      ctx.fillRect(width * 0.68, height * 0.16, width * 0.22, height * 0.62);
      ctx.strokeStyle = '#1E2631';
      ctx.strokeRect(width * 0.68, height * 0.16, width * 0.22, height * 0.62);

      // 2. Vẽ Bounding Boxes AI
      if (camera.boundingBoxes && camera.boundingBoxes.length > 0) {
        camera.boundingBoxes.forEach((box) => {
          const bx = box.x * width;
          const by = box.y * height;
          const bw = box.w * width;
          const bh = box.h * height;

          let color = '#3B82F6';
          if (box.severity === 'CRITICAL') color = '#EF4444';
          else if (box.severity === 'HIGH') color = '#F59E0B';

          // Khung viền góc vuông 0px
          ctx.strokeStyle = color;
          ctx.lineWidth = 2;
          ctx.strokeRect(bx, by, bw, bh);

          // Nhãn đối tượng trên đỉnh khung
          const labelText = box.label || 'TARGET';
          ctx.font = 'bold 9px "JetBrains Mono", monospace';
          const textMetrics = ctx.measureText(labelText);
          const tagWidth = textMetrics.width + 10;
          const tagHeight = 14;

          ctx.fillStyle = color;
          ctx.fillRect(bx, by - tagHeight, tagWidth, tagHeight);

          ctx.fillStyle = '#FFFFFF';
          ctx.fillText(labelText, bx + 5, by - 3);

          // Tâm định vị đối tượng
          ctx.fillStyle = color;
          ctx.fillRect(bx + bw / 2 - 2, by + bh / 2 - 2, 4, 4);
        });
      }

      // Hiệu ứng scanline mờ đặc trưng CCTV
      ctx.fillStyle = 'rgba(255, 255, 255, 0.02)';
      for (let i = 0; i < height; i += 4) {
        ctx.fillRect(0, i, width, 1);
      }
    };

    render();
    const handleResize = () => render();
    window.addEventListener('resize', handleResize);

    return () => {
      if (animationFrameId !== undefined) {
        cancelAnimationFrame(animationFrameId);
      }
      window.removeEventListener('resize', handleResize);
    };
  }, [canvasRef, camera]);
}
