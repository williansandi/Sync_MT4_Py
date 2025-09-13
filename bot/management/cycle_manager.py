import logging

class CycleManager:
    def __init__(self, config, log_callback, trade_logger):
        self.log_callback = log_callback # For general logs (UI display)
        self.trade_logger = trade_logger # For trade-specific logs (file)
        self.reload_config(config)
        self.reset()

    def reload_config(self, config):
        self.config = config
        self.initial_entry_value = float(self.config.get('valor_entrada', 1.0))
        self.martingale_factor = float(self.config.get('fator_martingale', 2.1))
        
        profile_name = self.config.get('perfil_de_risco', 'MODERADO').lower()
        
        # Carrega os parâmetros do perfil ativo a partir da configuração geral
        self.active_profile = {
            'percentual_recuperacao': float(self.config.get(f'{profile_name}_recuperacao', 75)) / 100.0,
            'max_gales_por_ciclo': int(self.config.get(f'{profile_name}_max_gales', 2)),
            'max_ciclos_perdidos': int(self.config.get(f'{profile_name}_max_ciclos', 2)),
        }
        
        self.log_callback(f"Perfil de Risco definido para: {profile_name.upper()}", "CONFIG")
        logging.info(f"CycleManager configurado com perfil: {profile_name.upper()} | {self.active_profile}")

    def reset(self):
        self.current_gale = 0
        self.lost_cycles_count = 0
        self.current_cycle_loss = 0.0
        self.last_entry_value = 0.0
        self.is_active = True
        self.trade_logger.info("[INFO] Gerenciador de Ciclos resetado.")

    def get_next_entry_value(self, payout):
        if not self.is_active:
            return 0

        if self.current_gale == 0:
            if self.current_cycle_loss == 0:
                entry_value = self.initial_entry_value
            else:
                if payout <= 0:
                    self.log_callback("Payout inválido (<= 0) para cálculo de recuperação. Usando entrada inicial.", "ERRO")
                    return self.initial_entry_value
                
                recovery_percentage = self.active_profile['percentual_recuperacao']
                profit_target = self.current_cycle_loss * recovery_percentage
                entry_value = profit_target / payout
                self.trade_logger.info(f"[INFO] Iniciando Ciclo de Recuperação. Perda anterior: {self.current_cycle_loss:.2f}. Meta: {profit_target:.2f}. Entrada: {entry_value:.2f}")
        else:
            entry_value = self.last_entry_value * self.martingale_factor
        
        return max(entry_value, 1.0)

    def record_trade(self, profit, entry_value):
        if not self.is_active:
            return

        self.last_entry_value = entry_value

        if profit > 0:
            self.trade_logger.info(f"[WIN] WIN no Ciclo (Gale {self.current_gale}). Resetando gerenciamento.")
            self.current_cycle_loss = 0.0
            self.current_gale = 0
            self.lost_cycles_count = 0
        else:
            self.current_cycle_loss += entry_value
            self.current_gale += 1
            self.trade_logger.info(f"[LOSS] LOSS (Gale {self.current_gale-1}). Perda acumulada: {self.current_cycle_loss:.2f}")

            if self.current_gale > self.active_profile['max_gales_por_ciclo']:
                self.lost_cycles_count += 1
                self.trade_logger.warning(f"[AVISO] Ciclo perdido. Total de ciclos perdidos: {self.lost_cycles_count}")
                self.current_gale = 0 

                if self.lost_cycles_count >= self.active_profile['max_ciclos_perdidos']:
                    self.is_active = False
                    self.trade_logger.error(f"[STOP] Limite de {self.active_profile['max_ciclos_perdidos']} ciclos perdidos atingido. OPERAÇÕES PARADAS.")