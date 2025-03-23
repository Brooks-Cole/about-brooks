/**
 * Simplified data collection module
 */

// Main data collection object
const LolaDataCollector = {
  // Store collected data
  userData: {
    basic: {},
  },
  
  // Initialize data collection
  initialize: function() {
    console.log('Data collector initialized in simplified mode');
    return this;
  },
  
  // Get formatted data for prompt
  getFormattedDataForPrompt: function() {
    return '';
  },
  
  // Get all collected data
  getAllData: function() {
    return {
      basic: this.userData.basic,
      isEnhancedMode: false,
      lastUpdated: new Date()
    };
  },
  
  // Get stored preference
  getStoredPreference: function(key) {
    return null;
  },
  
  // Set user preference
  setUserPreference: function(key, value) {
    console.log(`Setting preference ${key} to ${value}`);
  },
  
  // Offer enhanced experience
  offerEnhancedExperience: function(callback) {
    console.log('Enhanced experience offer shown (simplified)');
    callback(false); // Default to basic experience
  }
};

export default LolaDataCollector;