class LevyFlightAnalyzer:
	""" """
	def estimate_levy_parameters(self, returns):
		"""Estimate Levy stable distribution parameters using MLE"""
		try:
			# ... (input validation and data cleaning) ...
			
			# Initial parameter guesses based on moments (kurtosis, skewness)
			alpha_init = np.clip(2.0 - np.abs(stats.kurtosis(returns_clean)) / 10, 1.1, 1.99)
			# ... (beta_init, gamma_init, delta_init) ...
			
			def levy_loglike(params):
				alpha, beta, gamma, delta = params
				# ... (bounds check) ...
				try:
					# Approximate log-likelihood
					centered_returns = (returns_clean - delta) / gamma
					if alpha == 2: # Gaussian case
						loglike = -0.5 * np.sum(centered_returns**2) - len(returns_clean) * np.log(gamma * np.sqrt(2*np.pi))
					else: # Approximation for general Levy case
						loglike = -np.sum(np.abs(centered_returns)**alpha) - len(returns_clean) * np.log(gamma)
					return -loglike
				except: return 1e10
			
			result = minimize(
				levy_loglike,
				[alpha_init, beta_init, gamma_init, delta_init],
				bounds=[(1.1, 1.99), (-0.99, 0.99), (1e-6, None), (None, None)],
				method='L-BFGS-B'
			)
			# ... (return results or initial guesses on failure) ...
		except Exception as e:
			# Fallback to simpler moment-based estimates if optimization fails
			# ... (fallback calculations) ...

	def detect_jumps(self, returns, alpha, gamma):
        """Detect jump events in the time series"""
        # ... (initialization) ...
        std_returns = returns / (gamma + 1e-10) # Standardize by Levy scale 'gamma'
        threshold = self.config.jump_threshold
        
        for i in range(len(returns)):
            if np.abs(std_returns[i]) > threshold:
                # Check if it's a true jump or just high volatility in a local window
                local_vol = np.std(returns[max(0, i-5):i+6])
                if np.abs(returns[i]) > threshold * local_vol: # Compare raw return to local vol
                    jumps[i] = 1
                    jump_magnitudes[i] = returns[i]
        return jumps, jump_magnitudes
	
	def identify_regime(self, returns, jumps):
        # ... (input validation) ...
        jump_intensity = np.sum(jumps[-10:]) / 10 # Proportion of jumps in last 10 periods
        
        if jump_intensity > self.config.diffusion_threshold:
            new_regime = 'jump'
        else:
            new_regime = 'diffusion'
        
        # Apply persistence to avoid rapid switching
        if hasattr(self, 'regime_state') and self.regime_state != new_regime:
            if np.random.random() > (1 - self.config.regime_persistence):
                new_regime = self.regime_state # Keep old regime with some probability
        
        self.regime_state = new_regime
        return new_regime
	
	def calculate_levy_momentum(self, returns, jumps, jump_magnitudes, regime):
        # ... (input validation and slicing) ...
        
        # Jump-driven momentum: exponentially weighted average of recent jump magnitudes
        jump_momentum = 0.0
        if np.sum(recent_jumps) > 0:
            jump_returns = recent_jump_mags[recent_jumps == 1]
            if len(jump_returns) > 0:
                weights = np.array([self.config.jump_signal_decay**i for i in range(len(jump_returns))])
                weights = weights[::-1] # More recent jumps get higher weight
                jump_momentum = np.average(jump_returns, weights=weights)
        
        # Diffusion momentum: simple mean of recent non-jump returns
        diffusion_returns = recent_returns[recent_jumps == 0]
        diffusion_momentum = 0.0
        if len(diffusion_returns) > 0:
            diffusion_momentum = np.mean(diffusion_returns)
            
        return jump_momentum, diffusion_momentum