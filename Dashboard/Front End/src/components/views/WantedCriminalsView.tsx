import React, { useState, useEffect } from 'react';
import {
  UserX,
  Plus,
  Trash2,
  Edit2,
  FileCheck2,
  ShieldAlert,
  Search,
  Filter,
  Eye,
  CheckCircle2,
  AlertTriangle,
  X,
  Camera,
  Hash,
  Clock
} from 'lucide-react';
import { IWantedPerson, IIncidentItem } from '../../types/soc.ts';

interface WantedCriminalsViewProps {
  incidents?: IIncidentItem[];
  onToast?: (msg: string) => void;
}

export const WantedCriminalsView: React.FC<WantedCriminalsViewProps> = ({
  incidents = [],
  onToast,
}) => {
  const [wantedList, setWantedList] = useState<IWantedPerson[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [filterLevel, setFilterLevel] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Modals state
  const [selectedPerson, setSelectedPerson] = useState<IWantedPerson | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [isStampModalOpen, setIsStampModalOpen] = useState<boolean>(false);

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    alias: '',
    threatLevel: 'HIGH' as 'CRITICAL' | 'HIGH' | 'MEDIUM',
    status: 'WANTED' as 'WANTED' | 'RED_ALERT' | 'MONITORING' | 'APPREHENDED',
    charges: '',
    height: '1m70',
    build: 'Trung bình',
    clothing: 'Áo khoác tối màu',
    distinguishingMarks: 'Sẹo hoặc hình xăm',
    lastSeenCameraId: 'CAM_01',
    lastSeenLocation: 'Cổng Chính Chu Văn An',
  });

  const [stampData, setStampData] = useState({
    incidentId: '',
    evidenceType: 'KEYFRAME_SNAPSHOT' as 'KEYFRAME_SNAPSHOT' | 'VIDEO_CLIP' | 'FORENSIC_CROP',
    notes: 'Bằng chứng ghi nhận nghi phạm từ AI surveillance camera',
  });

  const fetchWantedList = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/v1/wanted');
      if (res.ok) {
        const data = await res.json();
        setWantedList(data.data || []);
      }
    } catch {
      // Offline fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWantedList();
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name: formData.name,
      alias: formData.alias,
      threatLevel: formData.threatLevel,
      status: formData.status,
      charges: formData.charges.split(',').map((c) => c.trim()).filter(Boolean),
      identificationFeatures: {
        height: formData.height,
        build: formData.build,
        clothing: formData.clothing,
        distinguishingMarks: formData.distinguishingMarks,
      },
      lastSeenCameraId: formData.lastSeenCameraId,
      lastSeenLocation: formData.lastSeenLocation,
    };

    try {
      const res = await fetch('/api/v1/wanted', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        onToast?.(`[TRUY NÃ] Đã thêm thành công hồ sơ đối tượng ${formData.name}`);
        setIsCreateModalOpen(false);
        fetchWantedList();
      }
    } catch {
      onToast?.('[LỖI] Không thể tạo hồ sơ truy nã');
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPerson) return;

    const payload = {
      name: formData.name,
      alias: formData.alias,
      threatLevel: formData.threatLevel,
      status: formData.status,
      charges: formData.charges.split(',').map((c) => c.trim()).filter(Boolean),
      identificationFeatures: {
        height: formData.height,
        build: formData.build,
        clothing: formData.clothing,
        distinguishingMarks: formData.distinguishingMarks,
      },
      lastSeenCameraId: formData.lastSeenCameraId,
      lastSeenLocation: formData.lastSeenLocation,
      operatorId: 'OP-VN-PSOC-804',
    };

    try {
      const res = await fetch(`/api/v1/wanted/${selectedPerson.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        onToast?.(`[CẬP NHẬT] Đã cập nhật hồ sơ đối tượng ${formData.name}`);
        setIsEditModalOpen(false);
        fetchWantedList();
      }
    } catch {
      onToast?.('[LỖI] Không thể cập nhật hồ sơ');
    }
  };

  const handleDelete = async (personId: string, personName: string) => {
    if (!window.confirm(`Bạn có chắc muốn xóa hồ sơ truy nã của ${personName} (${personId})?`)) return;

    try {
      const res = await fetch(`/api/v1/wanted/${personId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        onToast?.(`[ĐÃ XÓA] Đã xóa hồ sơ truy nã ${personName}`);
        fetchWantedList();
      }
    } catch {
      onToast?.('[LỖI] Không thể xóa hồ sơ');
    }
  };

  const handleStampEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPerson) return;

    const chosenIncident = incidents.find((i) => i.id === stampData.incidentId);
    const payload = {
      incidentId: stampData.incidentId || `INC-${Date.now()}`,
      evidenceType: stampData.evidenceType,
      evidenceUrl: chosenIncident?.playbackUrl || `/api/v1/cameras/${selectedPerson.lastSeenCameraId || 'cam_01'}/snapshot`,
      notes: stampData.notes,
      stampedBy: 'OP-VN-PSOC-804',
      sha256Hash: `SHA256-${Date.now()}-CERTIFIED-CRIME-EVIDENCE`,
    };

    try {
      const res = await fetch(`/api/v1/wanted/${selectedPerson.id}/evidence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        onToast?.(`[ĐÓNG DẤU BẰNG CHỨNG] Đã đóng dấu chứng thực pháp y cho ${selectedPerson.name}!`);
        setIsStampModalOpen(false);
        fetchWantedList();
      }
    } catch {
      onToast?.('[LỖI] Không thể đóng dấu bằng chứng');
    }
  };

  const openEditModal = (person: IWantedPerson) => {
    setSelectedPerson(person);
    setFormData({
      name: person.name,
      alias: person.alias || '',
      threatLevel: person.threatLevel,
      status: person.status,
      charges: person.charges.join(', '),
      height: person.identificationFeatures?.height || '1m70',
      build: person.identificationFeatures?.build || 'Trung bình',
      clothing: person.identificationFeatures?.clothing || 'Áo khoác',
      distinguishingMarks: person.identificationFeatures?.distinguishingMarks || 'Không có',
      lastSeenCameraId: person.lastSeenCameraId || 'CAM_01',
      lastSeenLocation: person.lastSeenLocation || 'Khu vực camera',
    });
    setIsEditModalOpen(true);
  };

  const openStampModal = (person: IWantedPerson) => {
    setSelectedPerson(person);
    setStampData({
      incidentId: incidents[0]?.id || 'INC-2026-0842',
      evidenceType: 'KEYFRAME_SNAPSHOT',
      notes: `Đóng dấu chứng thực hành vi tội phạm từ camera ${person.lastSeenCameraId || 'CAM_01'}`,
    });
    setIsStampModalOpen(true);
  };

  const filteredList = wantedList.filter((p) => {
    const matchSearch =
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.alias && p.alias.toLowerCase().includes(searchTerm.toLowerCase())) ||
      p.charges.some((c) => c.toLowerCase().includes(searchTerm.toLowerCase())) ||
      p.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchLevel = filterLevel === 'ALL' || p.threatLevel === filterLevel;
    return matchSearch && matchLevel;
  });

  return (
    <div className="space-y-4 select-none min-w-0">
      {/* Thanh Tiêu đề & Tác vụ */}
      <div className="bg-[#0E131A] border border-[#1E2631] px-4 py-3 flex items-center justify-between min-w-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#7F1D1D]/30 border border-[#DC2626] flex items-center justify-center shrink-0">
            <UserX className="w-4 h-4 text-[#EF4444]" />
          </div>
          <div>
            <div className="font-bold text-sm text-white tracking-wide flex items-center gap-2">
              <span>HỒ SƠ ĐỐI TƯỢNG TRUY NÃ & ĐÓNG DẤU BẰNG CHỨNG HÌNH SỰ</span>
              <span className="bg-[#991B1B] text-white text-[10px] font-mono px-2 py-0.5 border border-[#DC2626]">
                {wantedList.length} ĐỐI TƯỢNG
              </span>
            </div>
            <div className="text-[11px] font-mono text-slate-400">
              Quản trị cơ sở dữ liệu đối tượng nguy hiểm • Đóng dấu pháp y SHA-256 từ AI Camera Stream
            </div>
          </div>
        </div>

        <button
          onClick={() => {
            setFormData({
              name: '',
              alias: '',
              threatLevel: 'HIGH',
              status: 'WANTED',
              charges: 'Cướp giật tài sản, Gây rối trật tự',
              height: '1m72',
              build: 'Gầy',
              clothing: 'Áo khoác gió đen',
              distinguishingMarks: 'Sẹo mắt phải',
              lastSeenCameraId: 'CAM_01',
              lastSeenLocation: 'Cổng Chính Chu Văn An',
            });
            setIsCreateModalOpen(true);
          }}
          className="px-3.5 py-1.5 bg-[#10B981] hover:bg-[#059669] text-black font-mono font-bold text-xs inline-flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>THÊM HỒ SƠ TRUY NÃ</span>
        </button>
      </div>

      {/* Thanh Tìm kiếm & Bộ lọc */}
      <div className="bg-[#0A0E17] border border-[#1E2631] p-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Tìm theo tên đối tượng, bí danh, mã hồ sơ hoặc tội danh..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#111823] border border-[#243042] text-xs text-white px-3 py-1.5 focus:border-[#10B981] focus:outline-none font-mono"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[11px] font-mono text-slate-400">Mức độ rủi ro:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((lvl) => (
            <button
              key={lvl}
              onClick={() => setFilterLevel(lvl)}
              className={`px-2.5 py-1 text-[11px] font-mono border transition-colors ${
                filterLevel === lvl
                  ? lvl === 'CRITICAL'
                    ? 'bg-[#7F1D1D] border-[#DC2626] text-white font-bold'
                    : lvl === 'HIGH'
                    ? 'bg-[#78350F] border-[#F59E0B] text-white font-bold'
                    : lvl === 'MEDIUM'
                    ? 'bg-[#1E293B] border-[#06B6D4] text-[#06B6D4] font-bold'
                    : 'bg-[#10B981] border-[#10B981] text-black font-bold'
                  : 'bg-[#111823] border-[#243042] text-slate-400 hover:text-white'
              }`}
            >
              {lvl === 'ALL' ? 'TẤT CẢ' : lvl}
            </button>
          ))}
        </div>
      </div>

      {/* Danh sách Thẻ Đối Tượng Truy Nã */}
      {isLoading ? (
        <div className="bg-[#0E131A] border border-[#1E2631] p-12 text-center text-slate-400 font-mono text-xs">
          Đang tải cơ sở dữ liệu đối tượng truy nã...
        </div>
      ) : filteredList.length === 0 ? (
        <div className="bg-[#0E131A] border border-[#1E2631] p-12 text-center text-slate-400 font-mono text-xs">
          Không tìm thấy hồ sơ đối tượng truy nã phù hợp.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredList.map((person) => {
            const isCritical = person.threatLevel === 'CRITICAL';
            const isHigh = person.threatLevel === 'HIGH';
            const stampCount = person.evidenceStamps?.length || 0;

            return (
              <div
                key={person.id}
                className={`bg-[#0A0E17] border flex flex-col justify-between transition-all duration-200 ${
                  isCritical
                    ? 'border-[#DC2626] shadow-lg shadow-red-950/20'
                    : isHigh
                    ? 'border-[#F59E0B]'
                    : 'border-[#1E2631]'
                }`}
              >
                {/* Header Thẻ */}
                <div className="p-3.5 border-b border-[#1E2631] flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-10 h-10 border border-[#243042] bg-[#161E29] flex items-center justify-center font-bold text-slate-300 text-sm overflow-hidden shrink-0">
                      {person.avatarUrl && person.avatarUrl.endsWith('.jpg') ? (
                        <img
                          src={person.avatarUrl}
                          alt={person.name}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      ) : (
                        <UserX className="w-5 h-5 text-slate-400" />
                      )}
                    </div>
                    <div>
                      <div className="font-bold text-sm text-white flex items-center gap-2">
                        <span>{person.name}</span>
                        {person.alias && (
                          <span className="text-xs font-mono text-[#06B6D4]">({person.alias})</span>
                        )}
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">Mã: {person.id}</div>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1">
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 border uppercase ${
                        isCritical
                          ? 'bg-[#7F1D1D] border-[#DC2626] text-white animate-pulse'
                          : isHigh
                          ? 'bg-[#78350F] border-[#F59E0B] text-amber-200'
                          : 'bg-[#1E293B] border-[#06B6D4] text-[#06B6D4]'
                      }`}
                    >
                      {person.threatLevel}
                    </span>
                    <span className="text-[9px] font-mono text-slate-400 uppercase">
                      {person.status}
                    </span>
                  </div>
                </div>

                {/* Nội dung chi tiết */}
                <div className="p-3.5 space-y-2.5 text-xs flex-1">
                  {/* Tội danh */}
                  <div>
                    <span className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
                      Tội danh truy nã:
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {person.charges.map((charge, cIdx) => (
                        <span
                          key={cIdx}
                          className="bg-[#161E29] border border-[#243042] text-slate-200 text-[10px] font-mono px-2 py-0.5"
                        >
                          {charge}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Đặc điểm nhận diện */}
                  <div className="bg-[#111823] p-2 border border-[#1E2631] space-y-1 font-mono text-[11px]">
                    <div className="text-slate-300">
                      <span className="text-slate-500">Vóc dáng:</span> {person.identificationFeatures?.height} &bull; {person.identificationFeatures?.build}
                    </div>
                    <div className="text-slate-300">
                      <span className="text-slate-500">Trang phục:</span> {person.identificationFeatures?.clothing}
                    </div>
                    <div className="text-amber-400">
                      <span className="text-slate-500">Nhận dạng:</span> {person.identificationFeatures?.distinguishingMarks}
                    </div>
                  </div>

                  {/* Vị trí phát hiện gần nhất */}
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1">
                    <span className="inline-flex items-center gap-1 text-[#06B6D4]">
                      <Camera className="w-3.5 h-3.5" />
                      {person.lastSeenCameraId} ({person.lastSeenLocation})
                    </span>
                    <span className="inline-flex items-center gap-1 text-slate-500">
                      <Clock className="w-3 h-3" />
                      {new Date(person.lastSeenTimestamp || Date.now()).toLocaleTimeString()}
                    </span>
                  </div>

                  {/* Khu vực Bằng Chứng Đã Đóng Dấu */}
                  <div className="border-t border-[#1E2631] pt-2">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-mono text-slate-400 uppercase flex items-center gap-1">
                        <FileCheck2 className="w-3.5 h-3.5 text-[#10B981]" />
                        Bằng chứng pháp y ({stampCount})
                      </span>
                      {stampCount > 0 ? (
                        <span className="text-[9px] font-mono text-[#10B981] font-bold">
                          ĐÃ ĐÓNG DẤU
                        </span>
                      ) : (
                        <span className="text-[9px] font-mono text-slate-500">
                          CHƯA CÓ BẰNG CHỨNG
                        </span>
                      )}
                    </div>

                    {stampCount > 0 && person.evidenceStamps?.[0] && (
                      <div className="bg-[#0D1C18] border border-[#10B981]/40 p-2 text-[10px] font-mono text-slate-300 space-y-0.5">
                        <div className="text-[#10B981] font-bold truncate">
                          [DẤU] {person.evidenceStamps[0].stampId}
                        </div>
                        <div className="text-slate-400 truncate">
                          Hash: {person.evidenceStamps[0].sha256Hash.substring(0, 24)}...
                        </div>
                        <div className="text-slate-400">
                          Bởi: {person.evidenceStamps[0].stampedBy} &bull; {new Date(person.evidenceStamps[0].stampedAt).toLocaleTimeString()}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Footer Buttons */}
                <div className="p-2.5 bg-[#0E131A] border-t border-[#1E2631] flex items-center justify-between gap-2">
                  <button
                    onClick={() => openStampModal(person)}
                    className="flex-1 py-1.5 bg-[#10B981]/10 border border-[#10B981] text-[#10B981] hover:bg-[#10B981] hover:text-black font-mono font-bold text-[11px] inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <FileCheck2 className="w-3.5 h-3.5" />
                    <span>ĐÓNG DẤU BẰNG CHỨNG</span>
                  </button>

                  <button
                    onClick={() => openEditModal(person)}
                    className="p-1.5 bg-[#161E29] border border-[#243042] text-slate-300 hover:text-white hover:border-slate-400 transition-colors cursor-pointer"
                    title="Chỉnh sửa hồ sơ"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => handleDelete(person.id, person.name)}
                    className="p-1.5 bg-[#161E29] border border-[#243042] text-red-400 hover:text-red-300 hover:border-red-500 transition-colors cursor-pointer"
                    title="Xóa hồ sơ"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* MODAL THÊM HỒ SƠ TRUY NÃ */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#0E131A] border border-[#1E2631] w-full max-w-lg p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-[#1E2631] pb-3">
              <div className="font-bold text-sm text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-[#10B981]" />
                <span>THÊM HỒ SƠ TRUY NÃ MỚI</span>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-3 font-mono text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Họ và tên đối tượng *</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                    placeholder="VD: Nguyễn Văn A"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Bí danh / Biệt danh</label>
                  <input
                    type="text"
                    value={formData.alias}
                    onChange={(e) => setFormData({ ...formData, alias: e.target.value })}
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                    placeholder="VD: Tèo Ruồi"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Mức độ rủi ro</label>
                  <select
                    value={formData.threatLevel}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        threatLevel: e.target.value as 'CRITICAL' | 'HIGH' | 'MEDIUM',
                      })
                    }
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  >
                    <option value="CRITICAL">CRITICAL (Đặc biệt nguy hiểm)</option>
                    <option value="HIGH">HIGH (Nguy hiểm)</option>
                    <option value="MEDIUM">MEDIUM (Cảnh báo theo dõi)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Tình trạng</label>
                  <select
                    value={formData.status}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        status: e.target.value as 'WANTED' | 'RED_ALERT' | 'MONITORING' | 'APPREHENDED',
                      })
                    }
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  >
                    <option value="RED_ALERT">RED_ALERT (Lệnh truy nã đỏ)</option>
                    <option value="WANTED">WANTED (Đang truy nã)</option>
                    <option value="MONITORING">MONITORING (Đang bám vết)</option>
                    <option value="APPREHENDED">APPREHENDED (Đã tạm giữ)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Tội danh (phân cách dấu phẩy) *</label>
                <input
                  type="text"
                  required
                  value={formData.charges}
                  onChange={(e) => setFormData({ ...formData, charges: e.target.value })}
                  className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  placeholder="VD: Cướp giật tài sản, Cố ý gây thương tích"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Chiều cao & Vóc dáng</label>
                  <input
                    type="text"
                    value={formData.height}
                    onChange={(e) => setFormData({ ...formData, height: e.target.value })}
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Trang phục thường mặc</label>
                  <input
                    type="text"
                    value={formData.clothing}
                    onChange={(e) => setFormData({ ...formData, clothing: e.target.value })}
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Đặc điểm nhận diện đặc thù</label>
                <input
                  type="text"
                  value={formData.distinguishingMarks}
                  onChange={(e) => setFormData({ ...formData, distinguishingMarks: e.target.value })}
                  className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  placeholder="VD: Sẹo dài mí mắt, hình xăm rồng mu bàn tay"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Camera phát hiện</label>
                  <input
                    type="text"
                    value={formData.lastSeenCameraId}
                    onChange={(e) => setFormData({ ...formData, lastSeenCameraId: e.target.value })}
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Tên khu vực</label>
                  <input
                    type="text"
                    value={formData.lastSeenLocation}
                    onChange={(e) => setFormData({ ...formData, lastSeenLocation: e.target.value })}
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#1E2631]">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-3 py-1.5 bg-[#161E29] border border-[#243042] text-slate-300 hover:text-white cursor-pointer"
                >
                  HỦY
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-[#10B981] hover:bg-[#059669] text-black font-bold cursor-pointer"
                >
                  LƯU HỒ SƠ
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL SỬA HỒ SƠ */}
      {isEditModalOpen && selectedPerson && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#0E131A] border border-[#1E2631] w-full max-w-lg p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-[#1E2631] pb-3">
              <div className="font-bold text-sm text-white flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-[#06B6D4]" />
                <span>CHỈNH SỬA HỒ SƠ {selectedPerson.id}</span>
              </div>
              <button
                onClick={() => setIsEditModalOpen(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleEditSubmit} className="space-y-3 font-mono text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Họ và tên đối tượng</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Bí danh</label>
                  <input
                    type="text"
                    value={formData.alias}
                    onChange={(e) => setFormData({ ...formData, alias: e.target.value })}
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Mức độ rủi ro</label>
                  <select
                    value={formData.threatLevel}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        threatLevel: e.target.value as 'CRITICAL' | 'HIGH' | 'MEDIUM',
                      })
                    }
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Tình trạng</label>
                  <select
                    value={formData.status}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        status: e.target.value as 'WANTED' | 'RED_ALERT' | 'MONITORING' | 'APPREHENDED',
                      })
                    }
                    className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  >
                    <option value="RED_ALERT">RED_ALERT</option>
                    <option value="WANTED">WANTED</option>
                    <option value="MONITORING">MONITORING</option>
                    <option value="APPREHENDED">APPREHENDED</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Tội danh</label>
                <input
                  type="text"
                  required
                  value={formData.charges}
                  onChange={(e) => setFormData({ ...formData, charges: e.target.value })}
                  className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Đặc điểm nhận dạng</label>
                <input
                  type="text"
                  value={formData.distinguishingMarks}
                  onChange={(e) => setFormData({ ...formData, distinguishingMarks: e.target.value })}
                  className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#1E2631]">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="px-3 py-1.5 bg-[#161E29] border border-[#243042] text-slate-300 hover:text-white cursor-pointer"
                >
                  HỦY
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-[#06B6D4] hover:bg-[#0891B2] text-black font-bold cursor-pointer"
                >
                  CẬP NHẬT
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL ĐÓNG DẤU BẰNG CHỨNG PHÁP Y */}
      {isStampModalOpen && selectedPerson && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#0E131A] border-2 border-[#10B981] w-full max-w-lg p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-[#1E2631] pb-3">
              <div className="font-bold text-sm text-white flex items-center gap-2">
                <FileCheck2 className="w-5 h-5 text-[#10B981]" />
                <span>ĐÓNG DẤU BẰNG CHỨNG PHÁP Y CHO {selectedPerson.name}</span>
              </div>
              <button
                onClick={() => setIsStampModalOpen(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-[#0D1C18] border border-[#10B981]/50 p-3 font-mono text-xs text-slate-200 space-y-1">
              <div className="text-[#10B981] font-bold">
                MÃ HỒ SƠ: {selectedPerson.id} &bull; MỨC ĐỘ: {selectedPerson.threatLevel}
              </div>
              <div>
                Hành động này sẽ đóng dấu bằng chứng hình sự bất biến (SHA-256 Stamp) và liên kết sự cố AI phát hiện vào lý lịch tư pháp của đối tượng.
              </div>
            </div>

            <form onSubmit={handleStampEvidence} className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Chọn Sự cố / Snapshot tương ứng</label>
                <select
                  value={stampData.incidentId}
                  onChange={(e) => setStampData({ ...stampData, incidentId: e.target.value })}
                  className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                >
                  {incidents.length > 0 ? (
                    incidents.map((inc) => (
                      <option key={inc.id} value={inc.id}>
                        {inc.id} - {inc.title} ({inc.cameraId})
                      </option>
                    ))
                  ) : (
                    <option value="INC-2026-0842">INC-2026-0842 - CƯỚP GIẬT TÀI SẢN (cam_01)</option>
                  )}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Loại bằng chứng đóng dấu</label>
                <select
                  value={stampData.evidenceType}
                  onChange={(e) =>
                    setStampData({
                      ...stampData,
                      evidenceType: e.target.value as 'KEYFRAME_SNAPSHOT' | 'VIDEO_CLIP' | 'FORENSIC_CROP',
                    })
                  }
                  className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                >
                  <option value="KEYFRAME_SNAPSHOT">KEYFRAME SNAPSHOT (Ảnh trích xuất điểm đỉnh)</option>
                  <option value="VIDEO_CLIP">VIDEO CLIP (Đoạn ghi Rolling Buffer 10s)</option>
                  <option value="FORENSIC_CROP">FORENSIC CROP (Cắt cận cảnh hung khí / mặt)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Ghi chú nghiệp vụ điều tra *</label>
                <textarea
                  rows={3}
                  required
                  value={stampData.notes}
                  onChange={(e) => setStampData({ ...stampData, notes: e.target.value })}
                  className="w-full bg-[#111823] border border-[#243042] px-2.5 py-1.5 text-white focus:border-[#10B981] focus:outline-none"
                  placeholder="Ghi nhận lý do đóng dấu bằng chứng..."
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#1E2631]">
                <button
                  type="button"
                  onClick={() => setIsStampModalOpen(false)}
                  className="px-3 py-1.5 bg-[#161E29] border border-[#243042] text-slate-300 hover:text-white cursor-pointer"
                >
                  HỦY
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-[#10B981] hover:bg-[#059669] text-black font-bold inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <FileCheck2 className="w-4 h-4" />
                  <span>XÁC NHẬN ĐÓNG DẤU BẰNG CHỨNG</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
