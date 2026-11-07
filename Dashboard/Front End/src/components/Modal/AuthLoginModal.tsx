import React, { useState } from 'react';
import { Shield, Lock, User, LogIn, LogOut, CheckCircle2, AlertCircle } from 'lucide-react';
import { IOperatorSession } from '../../types/soc.ts';

interface AuthLoginModalProps {
  isOpen: boolean;
  session: IOperatorSession | null;
  onClose: () => void;
  onLoginSuccess: (session: IOperatorSession) => void;
  onLogout: () => void;
}

export const AuthLoginModal: React.FC<AuthLoginModalProps> = ({
  isOpen,
  session,
  onClose,
  onLoginSuccess,
  onLogout,
}) => {
  const [operatorId, setOperatorId] = useState<string>(session?.operatorId || 'OP-VN-SOC-804');
  const [operatorName, setOperatorName] = useState<string>(session?.operatorName || 'Trưởng Ca Trực SOC');
  const [shift, setShift] = useState<string>(session?.shift || 'Ca 1 · 06:00 - 14:00 UTC');
  const [password, setPassword] = useState<string>('soc2026');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!operatorId.trim() || !password.trim()) {
      setErrorMsg('Vui lòng nhập đầy đủ Mã Vận hành viên và Mật khẩu.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operatorId: operatorId.trim(),
          operatorName: operatorName.trim() || `Operator ${operatorId.trim()}`,
          shift,
          password: password.trim(),
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        setErrorMsg(data.error || 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.');
      } else {
        onLoginSuccess(data.session);
        onClose();
      }
    } catch {
      // Fallback local session if offline
      const fallbackSession: IOperatorSession = {
        token: `local_${Date.now()}`,
        operatorId: operatorId.trim(),
        operatorName: operatorName.trim() || `Operator ${operatorId.trim()}`,
        role: 'SOC_DUTY_OPERATOR',
        shift,
        loggedInAt: new Date().toISOString(),
      };
      onLoginSuccess(fallbackSession);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-[#05070A]/85 backdrop-blur-[2px] z-50 flex items-center justify-center p-4 select-none">
      <div className="w-[460px] max-w-full bg-[#0E131A] border border-[#1E2631] shadow-2xl">
        {/* Header */}
        <div className="bg-[#121822] border-b border-[#1E2631] px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#10B981]" />
            <span className="font-bold text-xs uppercase tracking-wider text-white font-mono">
              {session ? 'THÔNG TIN PHIÊN VẬN HÀNH VIÊN SOC' : 'XÁC THỰC VẬN HÀNH VIÊN SOC (AUTHENTICATION)'}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white font-mono text-xs font-bold cursor-pointer"
          >
            [ ✕ ĐÓNG ]
          </button>
        </div>

        {session ? (
          <div className="p-5 space-y-4 font-mono text-xs">
            <div className="bg-[#112224] border border-[#10B981] p-3 flex items-center gap-2.5 text-[#10B981]">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <div>
                <div className="font-bold">ĐÃ XÁC THỰC PHIÊN TÁC CHIẾN</div>
                <div className="text-[10px] text-slate-300 mt-0.5">
                  Đủ thẩm quyền thực thi chốt chặn Operational HITL [CD-04]
                </div>
              </div>
            </div>

            <div className="bg-[#121822] border border-[#1E2631] p-3.5 space-y-2 text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-500">MÃ OPERATOR:</span>
                <span className="text-white font-bold">{session.operatorId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">HỌ TÊN / CHỨC DANH:</span>
                <span className="text-[#10B981] font-bold">{session.operatorName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">CA TRỰC:</span>
                <span className="text-slate-200">{session.shift}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">THỜI ĐIỂM ĐĂNG NHẬP:</span>
                <span className="text-slate-400">{session.loggedInAt}</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#1E2631]">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 bg-[#161E29] border border-[#2D3748] text-slate-300 hover:text-white font-bold cursor-pointer"
              >
                ĐÓNG
              </button>
              <button
                type="button"
                onClick={() => {
                  onLogout();
                  onClose();
                }}
                className="px-3.5 py-1.5 bg-[#7F1D1D] border border-[#DC2626] text-white hover:bg-[#DC2626] font-bold inline-flex items-center gap-1.5 cursor-pointer"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>ĐĂNG XUẤT</span>
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-5 space-y-3.5 font-mono text-xs">
            {errorMsg && (
              <div className="bg-[#7F1D1D]/40 border border-[#DC2626] p-2.5 text-[#FECACA] flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-[#DC2626] shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div>
              <label className="block text-slate-400 mb-1">MÃ VẬN HÀNH VIÊN (OPERATOR ID):</label>
              <div className="flex items-center bg-[#05070A] border border-[#1E2631] px-2.5">
                <User className="w-3.5 h-3.5 text-slate-500 mr-2" />
                <input
                  type="text"
                  required
                  value={operatorId}
                  onChange={(e) => setOperatorId(e.target.value)}
                  placeholder="OP-VN-SOC-804"
                  className="w-full bg-transparent py-2 text-white focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">TÊN / CHỨC DANH CA TRỰC:</label>
              <input
                type="text"
                value={operatorName}
                onChange={(e) => setOperatorName(e.target.value)}
                placeholder="Trưởng Ca Trực SOC"
                className="w-full bg-[#05070A] border border-[#1E2631] px-3 py-2 text-white focus:outline-none focus:border-[#10B981]"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1">CA TRỰC TÁC CHIẾN:</label>
              <select
                value={shift}
                onChange={(e) => setShift(e.target.value)}
                className="w-full bg-[#05070A] border border-[#1E2631] px-3 py-2 text-white focus:outline-none focus:border-[#10B981]"
              >
                <option value="Ca 1 · 06:00 - 14:00 UTC">Ca 1 · 06:00 - 14:00 UTC</option>
                <option value="Ca 2 · 14:00 - 22:00 UTC">Ca 2 · 14:00 - 22:00 UTC</option>
                <option value="Ca 3 · 22:00 - 06:00 UTC">Ca 3 · 22:00 - 06:00 UTC</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">MẬT KHẨU XÁC THỰC:</label>
              <div className="flex items-center bg-[#05070A] border border-[#1E2631] px-2.5">
                <Lock className="w-3.5 h-3.5 text-slate-500 mr-2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Nhập mật khẩu (mặc định: soc2026)"
                  className="w-full bg-transparent py-2 text-white focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#1E2631]">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 bg-[#161E29] border border-[#2D3748] text-slate-400 hover:text-white font-bold cursor-pointer"
              >
                HỦY
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-1.5 bg-[#10B981] text-[#080B10] font-bold hover:bg-[#10B981]/90 inline-flex items-center gap-1.5 cursor-pointer"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>{isSubmitting ? 'ĐANG XÁC THỰC...' : 'ĐĂNG NHẬP SOC'}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
