import { create } from "zustand";

// Visibility and opacity per layer id. Layers themselves come from the API catalog.
type LayerUi = {
  visible: Record<string, boolean>;
  opacity: Record<string, number>;
  toggle: (id: string) => void;
  setVisible: (id: string, on: boolean) => void;
  setOpacity: (id: string, value: number) => void;
  cropFilter: string;
  setCropFilter: (crop: string) => void;
};

export const useLayerUi = create<LayerUi>((set) => ({
  visible: {},
  opacity: {},
  toggle: (id) => set((s) => ({ visible: { ...s.visible, [id]: !s.visible[id] } })),
  setVisible: (id, on) => set((s) => ({ visible: { ...s.visible, [id]: on } })),
  setOpacity: (id, value) => set((s) => ({ opacity: { ...s.opacity, [id]: value } })),
  cropFilter: "",
  setCropFilter: (crop) => set({ cropFilter: crop }),
}));

// Display order of groups in the panel and on the map (bottom to top).
export const GROUP_ORDER = ["Imagery", "Reference", "Indices", "Cropland", "Crop type", "Yield", "Boundaries"];

export const groupRank = (g: string) => {
  const i = GROUP_ORDER.indexOf(g);
  return i === -1 ? GROUP_ORDER.length : i;
};
