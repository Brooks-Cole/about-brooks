/**
 * data_collection.js
 * 
 * This script collects user data for enhancing the Lola AI experience.
 * It has two modes:
 * 1. Basic - collects minimal, non-intrusive data
 * 2. Enhanced - collects additional data when users opt-in
 */

// Main data collection object
const LolaDataCollector = {
  // Store collected data
  userData: {
    basic: {},
    enhanced: {}
  },
  
  // Configuration
  config: {
    isEnhancedMode: false,
    lastCollectionTime: null,
    collectionInterval: 60000, // Refresh data every minute
    speedTestImage: 'https://aboutbrooks.s3.us-east-1.amazonaws.com/speedtest.jpg'
  },
  
  /**
   * Initialize data collection
   * @param {Object} options - Configuration options
   */
  initialize: function(options = {}) {
    // Merge options with defaults
    this.config = { ...this.config, ...options };
    
    // Check for existing preferences
    this.config.isEnhancedMode = this.getStoredPreference('enhancedExperience') || false;
    
    // Start collection
    this.collectBasicData();
    
    // If enhanced mode is enabled, collect enhanced data
    if (this.config.isEnhancedMode) {
      this.collectEnhancedData();
    }
    
    // Set up periodic data refresh
    setInterval(() => this.refreshData(), this.config.collectionInterval);
    
    console.log('Lola Data Collector initialized:', 
                this.config.isEnhancedMode ? 'Enhanced Mode' : 'Basic Mode');
    
    return this;
  },
  
  /**
   * Get stored user preference
   * @param {string} key - Preference key
   * @returns {*} - Stored value or null
   */
  getStoredPreference: function(key) {
    try {
      return JSON.parse(localStorage.getItem(`lola_${key}`));
    } catch (e) {
      console.error('Error retrieving preference:', e);
      return null;
    }
  },
  
  /**
   * Set user preference
   * @param {string} key - Preference key
   * @param {*} value - Value to store
   */
  setUserPreference: function(key, value) {
    try {
      localStorage.setItem(`lola_${key}`, JSON.stringify(value));
      
      // Update enhanced mode setting if that's what changed
      if (key === 'enhancedExperience') {
        this.config.isEnhancedMode = value;
        
        // If enhanced mode was just enabled, collect enhanced data
        if (value) {
          this.collectEnhancedData();
        }
      }
    } catch (e) {
      console.error('Error storing preference:', e);
    }
  },
  
  /**
   * Refresh all data
   */
  refreshData: function() {
    this.collectBasicData();
    
    if (this.config.isEnhancedMode) {
      this.collectEnhancedData();
    }
    
    this.config.lastCollectionTime = new Date();
    console.log('Data refreshed at:', this.config.lastCollectionTime);
  },
  
  /**
   * Collect basic non-intrusive data
   */
  collectBasicData: function() {
    // Device & Browser Information
    this.userData.basic.deviceType = this.getDeviceType();
    this.userData.basic.browser = this.getBrowserInfo();
    this.userData.basic.screenSize = this.getScreenSize();
    this.userData.basic.timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    this.userData.basic.language = navigator.language || navigator.userLanguage;
    this.userData.basic.darkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Test connection speed (basic version)
    this.testConnectionSpeed((category) => {
      this.userData.basic.connectionSpeed = category;
    });
    
    // Session Information
    this.userData.basic.visitTime = new Date().toLocaleTimeString();
    this.userData.basic.referrer = document.referrer || 'Direct';
    
    // Update last collection time
    this.config.lastCollectionTime = new Date();
    
    console.log('Basic data collected');
    return this.userData.basic;
  },
  
  /**
   * Collect enhanced data (only when user has opted in)
   */
  collectEnhancedData: function() {
    if (!this.config.isEnhancedMode) {
      console.warn('Enhanced data collection attempted without opt-in');
      return null;
    }
    
    // Get more detailed location data if available
    this.getLocationData((locationData) => {
      this.userData.enhanced.location = locationData;
    });
    
    // Collect interaction patterns
    this.userData.enhanced.sessionDuration = this.getSessionDuration();
    this.userData.enhanced.clickPattern = this.getClickPattern();
    this.userData.enhanced.typingSpeed = this.getTypingSpeed();
    
    // Device capabilities
    this.userData.enhanced.hasWebcam = this.checkForWebcam();
    this.userData.enhanced.hasMicrophone = this.checkForMicrophone();
    this.userData.enhanced.batteryStatus = this.getBatteryStatus();
    this.userData.enhanced.connectionType = this.getConnectionType();
    
    // Detailed browser and system info
    this.userData.enhanced.userAgent = navigator.userAgent;
    this.userData.enhanced.operatingSystem = this.getOperatingSystem();
    this.userData.enhanced.browserPlugins = this.getBrowserPlugins();
    
    console.log('Enhanced data collected');
    return this.userData.enhanced;
  },
  
  /**
   * Get device type (mobile, tablet, desktop)
   * @returns {string} - Device type
   */
  getDeviceType: function() {
    const width = window.innerWidth;
    if (width < 768) return 'mobile';
    if (width < 1024) return 'tablet';
    return 'desktop';
  },
  
  /**
   * Get browser information
   * @returns {Object} - Browser name and version
   */
  getBrowserInfo: function() {
    const ua = navigator.userAgent;
    let browser = 'Unknown';
    let version = 'Unknown';
    
    // Extract browser and version
    if (ua.indexOf('Chrome') > -1) {
      browser = 'Chrome';
      version = ua.match(/Chrome\/(\d+\.\d+)/)[1];
    } else if (ua.indexOf('Firefox') > -1) {
      browser = 'Firefox';
      version = ua.match(/Firefox\/(\d+\.\d+)/)[1];
    } else if (ua.indexOf('Safari') > -1) {
      browser = 'Safari';
      version = ua.match(/Version\/(\d+\.\d+)/)[1];
    } else if (ua.indexOf('Edge') > -1) {
      browser = 'Edge';
      version = ua.match(/Edge\/(\d+\.\d+)/)[1];
    } else if (ua.indexOf('MSIE') > -1 || ua.indexOf('Trident/') > -1) {
      browser = 'Internet Explorer';
      version = ua.match(/(?:MSIE |rv:)(\d+\.\d+)/)[1];
    }
    
    return { name: browser, version: version };
  },
  
  /**
   * Get screen size and resolution
   * @returns {Object} - Screen width, height and pixel ratio
   */
  getScreenSize: function() {
    return {
      width: window.innerWidth,
      height: window.innerHeight,
      pixelRatio: window.devicePixelRatio || 1
    };
  },
  
  /**
   * Test connection speed
   * @param {Function} callback - Callback function with speed category
   */
  testConnectionSpeed: function(callback) {
    const startTime = Date.now();
    const testImage = new Image();
    
    testImage.onload = function() {
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      // Determine speed category
      let speedCategory;
      if (duration < 100) {
        speedCategory = "lightning-fast";
      } else if (duration < 300) {
        speedCategory = "impressive";
      } else if (duration < 800) {
        speedCategory = "decent";
      } else if (duration < 1500) {
        speedCategory = "sluggish";
      } else {
        speedCategory = "patience-testing";
      }
      
      callback(speedCategory);
    };
    
    testImage.onerror = function() {
      callback("unknown");
    };
    
    // Load a small image from your server with cache-busting
    testImage.src = `${this.config.speedTestImage}?cache=${Date.now()}`;
  },
  
  /**
   * Get user's approximate location (city/country level)
   * @param {Function} callback - Callback function with location data
   */
  getLocationData: function(callback) {
    // Try to get geolocation if permitted
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          // Success - we have coordinates
          // Note: In a real implementation, you'd use a reverse geocoding service
          // to convert these coordinates to city/region names
          const locationData = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            timestamp: position.timestamp
          };
          callback(locationData);
        },
        (error) => {
          // Error or permission denied
          console.log('Geolocation error:', error.message);
          // Fall back to IP-based geolocation service
          this.getIPBasedLocation(callback);
        }
      );
    } else {
      // Geolocation not supported
      this.getIPBasedLocation(callback);
    }
  },
  
  /**
   * Get location based on IP address (using external service)
   * @param {Function} callback - Callback function with location data
   */
  getIPBasedLocation: function(callback) {
    // In a real implementation, you would call an IP geolocation API
    // For example: ipinfo.io, ipapi.co, etc.
    // This is a placeholder implementation
    
    fetch('https://ipapi.co/json/')
      .then(response => response.json())
      .then(data => {
        const locationData = {
          city: data.city,
          region: data.region,
          country: data.country_name,
          ip: data.ip
        };
        callback(locationData);
      })
      .catch(error => {
        console.error('IP location error:', error);
        callback({ error: 'Unable to determine location' });
      });
  },
  
  /**
   * Get session duration
   * @returns {number} - Session duration in seconds
   */
  getSessionDuration: function() {
    // Check if session start time is stored
    const sessionStart = this.getStoredPreference('sessionStart');
    
    if (!sessionStart) {
      // First time, set session start
      const now = Date.now();
      this.setUserPreference('sessionStart', now);
      return 0;
    }
    
    // Calculate duration
    return Math.floor((Date.now() - sessionStart) / 1000);
  },
  
  /**
   * Get click pattern (simplified)
   * @returns {Object} - Click metrics
   */
  getClickPattern: function() {
    // This would normally track clicks over time
    // Simplified implementation
    const clickCount = this.getStoredPreference('clickCount') || 0;
    
    return {
      totalClicks: clickCount,
      clickFrequency: this.getSessionDuration() > 0 ? 
        clickCount / (this.getSessionDuration() / 60) : 0 // clicks per minute
    };
  },
  
  /**
   * Calculate typing speed based on inputs
   * @returns {Object} - Typing speed metrics
   */
  getTypingSpeed: function() {
    // This would normally track keystrokes over time
    // Simplified implementation
    const keyCount = this.getStoredPreference('keyCount') || 0;
    
    return {
      totalKeys: keyCount,
      typingSpeed: this.getSessionDuration() > 0 ? 
        keyCount / (this.getSessionDuration() / 60) : 0 // keys per minute
    };
  },
  
  /**
   * Check if device has webcam
   * @returns {boolean} - True if webcam is available
   */
  checkForWebcam: function() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  },
  
  /**
   * Check if device has microphone
   * @returns {boolean} - True if microphone is available
   */
  checkForMicrophone: function() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  },
  
  /**
   * Get battery status if available
   * @returns {Object|null} - Battery information or null
   */
  getBatteryStatus: function() {
    if (!navigator.getBattery) {
      return null;
    }
    
    // This is asynchronous but we're returning a promise
    // In real implementation, you'd handle this with callbacks
    return navigator.getBattery().then(battery => {
      return {
        level: battery.level * 100,
        charging: battery.charging,
        chargingTime: battery.chargingTime,
        dischargingTime: battery.dischargingTime
      };
    }).catch(error => {
      console.error('Battery API error:', error);
      return null;
    });
  },
  
  /**
   * Get network connection type if available
   * @returns {string|null} - Connection type or null
   */
  getConnectionType: function() {
    if (!navigator.connection) {
      return null;
    }
    
    return navigator.connection.effectiveType || null;
  },
  
  /**
   * Get operating system
   * @returns {string} - Operating system name
   */
  getOperatingSystem: function() {
    const ua = navigator.userAgent;
    
    if (ua.indexOf('Windows') !== -1) return 'Windows';
    if (ua.indexOf('Mac') !== -1) return 'MacOS';
    if (ua.indexOf('Linux') !== -1) return 'Linux';
    if (ua.indexOf('Android') !== -1) return 'Android';
    if (ua.indexOf('iOS') !== -1 || ua.indexOf('iPhone') !== -1 || ua.indexOf('iPad') !== -1) return 'iOS';
    
    return 'Unknown';
  },
  
  /**
   * Get installed browser plugins (limited)
   * @returns {Array} - List of plugin names
   */
  getBrowserPlugins: function() {
    if (!navigator.plugins || navigator.plugins.length === 0) {
      return [];
    }
    
    const plugins = [];
    for (let i = 0; i < navigator.plugins.length; i++) {
      plugins.push(navigator.plugins[i].name);
    }
    
    return plugins;
  },
  
  /**
   * Present opt-in modal for enhanced experience
   * @param {Function} callback - Callback after user decision
   */
  offerEnhancedExperience: function(callback) {
    // Create styled modal matching the app's design
    
    const modal = document.createElement('div');
    modal.className = 'data-collector-modal';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(44, 62, 80, 0.8);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      backdrop-filter: blur(5px);
      animation: fadeIn 0.3s ease-in-out;
    `;
    
    const content = document.createElement('div');
    content.className = 'data-collector-content';
    content.style.cssText = `
      background: white;
      padding: 30px;
      border-radius: 10px;
      max-width: 500px;
      text-align: center;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
      animation: scaleIn 0.3s ease-in-out;
    `;
    
    const title = document.createElement('h2');
    title.textContent = 'Enhance Your Chat with Brooks';
    title.style.cssText = `
      color: #3498db;
      margin-bottom: 15px;
      font-size: 1.8rem;
    `;
    
    const body = document.createElement('p');
    body.textContent = 'Would you like to enable enhanced data collection to make your conversations with Brooks more personalized?';
    body.style.cssText = `
      color: #333;
      margin-bottom: 20px;
      line-height: 1.6;
    `;
    
    const privacyInfo = document.createElement('p');
    privacyInfo.style.cssText = `
      font-size: 0.9rem;
      color: #777;
      margin-bottom: 20px;
      background: #f8f9fa;
      padding: 12px;
      border-radius: 6px;
      text-align: left;
    `;
    privacyInfo.innerHTML = 'This includes data about: <br>• Your device and browser<br>• Your general location<br>• Your browsing patterns<br><br>This helps Brooks tailor his responses to your specific context.';
    
    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = `
      display: flex;
      justify-content: center;
      gap: 15px;
      margin-top: 25px;
    `;
    
    const basicButton = document.createElement('button');
    basicButton.textContent = 'Keep Basic';
    basicButton.style.cssText = `
      padding: 12px 20px;
      border: 1px solid #3498db;
      background: white;
      color: #3498db;
      border-radius: 25px;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
      transition: all 0.2s;
    `;
    
    const enhancedButton = document.createElement('button');
    enhancedButton.textContent = 'Enable Enhanced';
    enhancedButton.style.cssText = `
      padding: 12px 20px;
      border: none;
      background: #3498db;
      color: white;
      border-radius: 25px;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
      transition: all 0.2s;
      box-shadow: 0 2px 5px rgba(52, 152, 219, 0.3);
    `;
    
    // Add hover effects
    basicButton.onmouseover = function() {
      this.style.backgroundColor = '#f5f5f5';
    };
    basicButton.onmouseout = function() {
      this.style.backgroundColor = 'white';
    };
    
    enhancedButton.onmouseover = function() {
      this.style.backgroundColor = '#2980b9';
    };
    enhancedButton.onmouseout = function() {
      this.style.backgroundColor = '#3498db';
    };
    
    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      @keyframes scaleIn {
        from { transform: scale(0.9); opacity: 0; }
        to { transform: scale(1); opacity: 1; }
      }
    `;
    document.head.appendChild(style);
    
    // Event listeners
    basicButton.addEventListener('click', () => {
      this.setUserPreference('enhancedExperience', false);
      content.style.animation = 'scaleIn 0.3s ease-in-out reverse';
      modal.style.animation = 'fadeIn 0.3s ease-in-out reverse';
      setTimeout(() => {
        document.body.removeChild(modal);
      }, 300);
      if (callback) callback(false);
    });
    
    enhancedButton.addEventListener('click', () => {
      this.setUserPreference('enhancedExperience', true);
      this.collectEnhancedData();
      content.style.animation = 'scaleIn 0.3s ease-in-out reverse';
      modal.style.animation = 'fadeIn 0.3s ease-in-out reverse';
      setTimeout(() => {
        document.body.removeChild(modal);
      }, 300);
      if (callback) callback(true);
    });
    
    // Add close X button
    const closeButton = document.createElement('span');
    closeButton.innerHTML = '&times;';
    closeButton.style.cssText = `
      position: absolute;
      top: 10px;
      right: 15px;
      font-size: 24px;
      color: #999;
      cursor: pointer;
    `;
    closeButton.onclick = function() {
      // Consider this a rejection of enhanced mode
      basicButton.click();
    };
    
    // Append elements
    buttonContainer.appendChild(basicButton);
    buttonContainer.appendChild(enhancedButton);
    
    content.appendChild(closeButton);
    content.appendChild(title);
    content.appendChild(body);
    content.appendChild(privacyInfo);
    content.appendChild(buttonContainer);
    
    modal.appendChild(content);
    document.body.appendChild(modal);
  },
  
  /**
   * Get all collected data for use in the Lola system prompt
   * @returns {Object} - All collected data
   */
  getAllData: function() {
    return {
      basic: this.userData.basic,
      enhanced: this.config.isEnhancedMode ? this.userData.enhanced : null,
      isEnhancedMode: this.config.isEnhancedMode,
      lastUpdated: this.config.lastCollectionTime
    };
  },
  
  /**
   * Format data for insertion into system prompt
   * @returns {string} - Formatted data string
   */
  getFormattedDataForPrompt: function() {
    const data = this.getAllData();
    let promptData = `
# User Data Context
- Device: ${data.basic.deviceType || 'Unknown'}
- Browser: ${data.basic.browser ? `${data.basic.browser.name} ${data.basic.browser.version}` : 'Unknown'}
- Screen Size: ${data.basic.screenSize ? `${data.basic.screenSize.width}x${data.basic.screenSize.height}` : 'Unknown'}
- Time Zone: ${data.basic.timeZone || 'Unknown'}
- Language: ${data.basic.language || 'Unknown'}
- Dark Mode: ${data.basic.darkMode ? 'Enabled' : 'Disabled'}
- Connection Speed: ${data.basic.connectionSpeed || 'Unknown'}
- Visit Time: ${data.basic.visitTime || 'Unknown'}
- Referrer: ${data.basic.referrer || 'Direct'}
`;

    // Add enhanced data if available
    if (data.isEnhancedMode && data.enhanced) {
      promptData += `
# Enhanced User Context
- Location: ${data.enhanced.location ? 
    `${data.enhanced.location.city || ''}, ${data.enhanced.location.region || ''}, ${data.enhanced.location.country || ''}` 
    : 'Unknown'}
- Session Duration: ${data.enhanced.sessionDuration ? `${Math.floor(data.enhanced.sessionDuration / 60)} minutes` : 'Unknown'}
- Typing Speed: ${data.enhanced.typingSpeed ? `${Math.round(data.enhanced.typingSpeed)} keys per minute` : 'Unknown'}
- Operating System: ${data.enhanced.operatingSystem || 'Unknown'}
- Connection Type: ${data.enhanced.connectionType || 'Unknown'}
- Device Capabilities: ${data.enhanced.hasWebcam ? 'Has webcam, ' : ''}${data.enhanced.hasMicrophone ? 'Has microphone' : ''}
- Battery Status: ${data.enhanced.batteryStatus ? 
    `${Math.round(data.enhanced.batteryStatus.level)}% (${data.enhanced.batteryStatus.charging ? 'Charging' : 'Not charging'})` 
    : 'Unknown'}
`;
    }
    
    return promptData;
  }
};

// Usage example
// LolaDataCollector.initialize();

// After a while, offer enhanced experience
// setTimeout(() => {
//   LolaDataCollector.offerEnhancedExperience();
// }, 60000); // After 1 minute

// When generating the system prompt, include:
// const systemPrompt = existingPrompt + LolaDataCollector.getFormattedDataForPrompt();

export default LolaDataCollector;