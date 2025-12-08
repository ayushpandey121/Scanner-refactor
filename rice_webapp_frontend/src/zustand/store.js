import { create } from 'zustand';

const useRiceStore = create((set, get) => ({
  grains: null,
  reportData: null,
  previewImage: null,
  croppedImageUrl: null,
  fileName: null,
  date: null,
  selectedGrainId: null,
  hoveredGrainId: null,
  historyData: null,
  selectedFile: null,
  parameters: null,
  analysisStatus: null, // 'loading', 'completed', 'error'
  analysisError: null,
  sampleDetails: null,
  
  // NEW: Variety information fields
  selectedVariety: null,
  selectedSubVariety: null,
  selectedVarietyData: null,
  selectedSubVarietyData: null,

  setRiceData: (data) => {
    const state = {
      grains: data.grains,
      reportData: data.reportData,
      previewImage: data.previewImage,
      croppedImageUrl: data.croppedImageUrl || null,
      fileName: data.fileName,
      date: data.date,
      selectedFile: data.selectedFile,
      parameters: data.parameters,
      analysisStatus: data.analysisStatus,
      analysisError: data.analysisError,
      sampleDetails: data.sampleDetails || null,
      selectedGrainId: null,
      hoveredGrainId: null,
      // NEW: Include variety data if provided
      selectedVariety: data.selectedVariety !== undefined ? data.selectedVariety : get().selectedVariety,
      selectedSubVariety: data.selectedSubVariety !== undefined ? data.selectedSubVariety : get().selectedSubVariety,
      selectedVarietyData: data.selectedVarietyData !== undefined ? data.selectedVarietyData : get().selectedVarietyData,
      selectedSubVarietyData: data.selectedSubVarietyData !== undefined ? data.selectedSubVarietyData : get().selectedSubVarietyData,
    };

    // Save to localStorage
    try {
      // localStorage.setItem('riceAnalysisData', JSON.stringify(state));
    } catch (error) {
      console.warn('Failed to save to localStorage:', error);
    }

    set(state);
  },

  setSelectedGrainId: (id) => set({ selectedGrainId: id }),
  setHoveredGrainId: (id) => set({ hoveredGrainId: id }),
  setHistoryData: (data) => set({ historyData: data }),

  resetRiceData: () => {
    // Clear localStorage
    try {
      localStorage.removeItem('riceAnalysisData');
    } catch (error) {
      console.warn('Failed to clear localStorage:', error);
    }

    set({
      grains: null,
      reportData: null,
      previewImage: null,
      croppedImageUrl: null,
      fileName: null,
      date: null,
      selectedGrainId: null,
      hoveredGrainId: null,
      historyData: null,
      selectedFile: null,
      parameters: null,
      analysisStatus: null,
      analysisError: null,
      sampleDetails: null,
      // NEW: Reset variety data
      selectedVariety: null,
      selectedSubVariety: null,
      selectedVarietyData: null,
      selectedSubVarietyData: null,
    });
  },

  loadFromLocalStorage: () => {
    try {
      const savedData = localStorage.getItem('riceAnalysisData');
      if (savedData) {
        const parsedData = JSON.parse(savedData);
        set(parsedData);
        return true;
      }
    } catch (error) {
      console.warn('Failed to load from localStorage:', error);
    }
    return false;
  },

  setAnalysisStatus: (status, error = null) => set({
    analysisStatus: status,
    analysisError: error,
  }),

  updateChartDataFromGrains: () => {
    const grains = get().grains;
    const reportData = get().reportData;

    if (!grains || grains.length === 0) return;

    const categoryCounts = grains.reduce((acc, grain) => {
      const cat = grain.category?.[0] || "Unclassified";
      acc[cat] = (acc[cat] || 0) + 1;
      return acc;
    }, {});

    const total = reportData?.grainCount || grains.length;

    const chartData = Object.entries(categoryCounts).map(([cat, count]) => ({
      name: cat,
      count,
      percentage: ((count / total) * 100).toFixed(1),
    }));

    set({ chartData });
  },
})
);

export default useRiceStore;