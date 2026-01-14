import { create } from 'zustand';

export interface VideoEffect {
  id: string;
  type: 'erasure' | 'protection' | 'text';
  startTime: number;
  endTime: number;
  region: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface VideoMetadata {
  width: number;
  height: number;
  fps: number;
  totalFrames: number;
}

interface EffectsStore {
  effects: VideoEffect[];
  selectedEffectId: string | null;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  selectedLabel: 'erasure' | 'protection' | 'text';
  videoUrl: string;
  zoomLevel: number;  // Added for timeline zoom synchronization
  videoMetadata: VideoMetadata | null;  // Video dimensions and fps for speaker selection
  
  // Undo/Redo functionality
  history: VideoEffect[][];
  historyIndex: number;
  
  // Actions
  addEffect: (effect: VideoEffect) => void;
  updateEffect: (id: string, updates: Partial<VideoEffect>) => void;
  deleteEffect: (id: string) => void;
  setSelectedEffect: (id: string | null) => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setSelectedLabel: (label: 'erasure' | 'protection' | 'text') => void;
  setVideoUrl: (url: string) => void;
  setZoomLevel: (zoom: number) => void;  // Added zoom control
  setVideoMetadata: (metadata: VideoMetadata | null) => void;
  clearEffects: () => void;
  
  // Undo/Redo actions
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  saveToHistory: () => void;
  
  // Helper function to format for GhostCut API
  formatForGhostCut: () => any;
}

export const useEffectsStore = create<EffectsStore>((set, get) => ({
  effects: [],
  selectedEffectId: null,
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  selectedLabel: 'erasure',
  videoUrl: '',
  zoomLevel: 1,  // Default zoom level 1 (100%)
  videoMetadata: null,  // Will be set when video loads
  
  // Undo/Redo state
  history: [[]],
  historyIndex: 0,
  
  addEffect: (effect) => set((state) => {
    const newEffects = [...state.effects, effect];
    const newHistory = [...state.history.slice(0, state.historyIndex + 1), newEffects];
    return {
      effects: newEffects,
      history: newHistory.slice(-50), // Keep last 50 states
      historyIndex: Math.min(newHistory.length - 1, 49)
    };
  }),
  
  updateEffect: (id, updates) => set((state) => {
    const newEffects = state.effects.map(effect =>
      effect.id === id ? { ...effect, ...updates } : effect
    );
    const newHistory = [...state.history.slice(0, state.historyIndex + 1), newEffects];
    return {
      effects: newEffects,
      history: newHistory.slice(-50),
      historyIndex: Math.min(newHistory.length - 1, 49)
    };
  }),
  
  deleteEffect: (id) => set((state) => {
    const newEffects = state.effects.filter(effect => effect.id !== id);
    const newHistory = [...state.history.slice(0, state.historyIndex + 1), newEffects];
    return {
      effects: newEffects,
      selectedEffectId: state.selectedEffectId === id ? null : state.selectedEffectId,
      history: newHistory.slice(-50),
      historyIndex: Math.min(newHistory.length - 1, 49)
    };
  }),
  
  setSelectedEffect: (id) => set({ selectedEffectId: id }),
  
  setCurrentTime: (time) => set({ currentTime: time }),
  
  setDuration: (duration) => set({ duration }),
  
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  
  setSelectedLabel: (label) => set({ selectedLabel: label }),
  
  setVideoUrl: (url) => set({ videoUrl: url }),
  
  setZoomLevel: (zoom) => set({ zoomLevel: zoom }),

  setVideoMetadata: (metadata) => set({ videoMetadata: metadata }),

  clearEffects: () => set({ effects: [], selectedEffectId: null, history: [[]], historyIndex: 0 }),
  
  // Undo/Redo implementations
  undo: () => set((state) => {
    if (state.historyIndex > 0) {
      const newIndex = state.historyIndex - 1;
      return {
        effects: [...state.history[newIndex]],
        historyIndex: newIndex,
        selectedEffectId: null // Clear selection on undo
      };
    }
    return state;
  }),
  
  redo: () => set((state) => {
    if (state.historyIndex < state.history.length - 1) {
      const newIndex = state.historyIndex + 1;
      return {
        effects: [...state.history[newIndex]],
        historyIndex: newIndex,
        selectedEffectId: null // Clear selection on redo
      };
    }
    return state;
  }),
  
  canUndo: () => {
    const state = get();
    return state.historyIndex > 0;
  },
  
  canRedo: () => {
    const state = get();
    return state.historyIndex < state.history.length - 1;
  },
  
  saveToHistory: () => set((state) => {
    const newHistory = [...state.history.slice(0, state.historyIndex + 1), [...state.effects]];
    return {
      history: newHistory.slice(-50),
      historyIndex: Math.min(newHistory.length - 1, 49)
    };
  }),
  
  formatForGhostCut: () => {
    const state = get();
    
    // Transform to GhostCut API format
    // Note: The exact field names need to be confirmed with GhostCut API documentation
    const formattedEffects = state.effects.map(effect => ({
      type: effect.type,
      start_time: effect.startTime,
      end_time: effect.endTime,
      coordinates: {
        x: effect.region.x,
        y: effect.region.y,
        w: effect.region.width,
        h: effect.region.height
      }
    }));
    
    return {
      source_url: state.videoUrl,
      operations: formattedEffects
    };
  }
}));