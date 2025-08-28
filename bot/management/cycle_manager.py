# bot/management/cycle_manager.py
import logging

class CycleManager:
    """
    Gerencia os ciclos de operação, incluindo Martingale e estratégias de recuperação.
    """
    def __init__(self, config, log_callback):
        self.log_callback = log_callback
        self.reload_config(config)
        self.reset()

    def reload_config(self, config):
        """Carrega ou recarrega as configurações."""
        self.config = config
        self.management_type = self.config.get('management_type', 'agressivo').lower()
        self.initial_entry_value = float(self.config.get('valor_entrada', 1.0))
        self.martingale_levels = int(self.config.get('niveis_martingale', 2))
        self.martingale_factor = float(self.config.get('fator_martingale', 2.0))
        self.max_cycles = int(self.config.get('max_ciclos', 3))
        self.payout_for_recovery = float(self.config.get('payout_recuperacao', 87.0)) / 100.0

        logging.info(f"CycleManager configurado: Tipo={self.management_type}, Ciclos={self.max_cycles}, Martingale={self.martingale_levels} níveis")

    def reset(self):
        """Reseta o estado do gerenciamento para o início."""
        self.current_cycle = 1
        self.current_martingale_level = 0
        self.accumulated_loss_cycle = 0.0
        self.total_loss_to_recover = 0.0
        self.is_active = True
        self.log_callback("Gerenciador de Ciclos resetado para o estado inicial.", "INFO")

    def get_next_entry_value(self):
        """Calcula e retorna o valor da próxima entrada."""
        if not self.is_active:
            return 0

        # Modo Agressivo: Martingale de ciclos
        if self.management_type == 'agressivo':
            if self.current_martingale_level == 0:
                # Início de um novo ciclo
                if self.current_cycle == 1:
                    return self.initial_entry_value
                else:
                    # Entrada de recuperação para ciclos > 1
                    if self.payout_for_recovery <= 0:
                        self.log_callback("Payout de recuperação inválido. Abortando.", "ERRO")
                        self.is_active = False
                        return 0
                    return self.total_loss_to_recover / self.payout_for_recovery
            else:
                # Dentro de um ciclo, aplicando Martingale
                previous_entry = self.get_previous_entry_value()
                return previous_entry * self.martingale_factor

        # Modo Conservador: Recuperação gradual (a ser implementado)
        elif self.management_type == 'conservador':
            # Por enquanto, opera de forma simples sem recuperação entre ciclos
            if self.current_martingale_level > 0:
                 previous_entry = self.get_previous_entry_value()
                 return previous_entry * self.martingale_factor
            return self.initial_entry_value
            
        return self.initial_entry_value

    def get_previous_entry_value(self):
        """Helper para pegar o valor da entrada anterior no mesmo ciclo."""
        if self.current_martingale_level == 1:
            if self.current_cycle == 1:
                return self.initial_entry_value
            else:
                return self.total_loss_to_recover / self.payout_for_recovery
        else: # Martingale nivel 2+
            # Recalcula o caminho para trás
            previous_level_entry = self.get_previous_entry_value_at_level(self.current_martingale_level - 1)
            return previous_level_entry

    def get_previous_entry_value_at_level(self, level):
        """Calcula o valor de entrada para um nível de martingale específico."""
        if level == 0:
            if self.current_cycle == 1:
                return self.initial_entry_value
            else:
                return self.total_loss_to_recover / self.payout_for_recovery
        
        base_value = self.get_previous_entry_value_at_level(level - 1)
        return base_value * self.martingale_factor

    def record_trade(self, profit, entry_value):
        """Registra o resultado de um trade e atualiza o estado."""
        if not self.is_active:
            return

        if profit > 0:
            # WIN
            self.log_callback(f"WIN no Ciclo {self.current_cycle} (Gale {self.current_martingale_level}). Resetando ciclo.", "WIN")
            if self.management_type == 'agressivo':
                self.total_loss_to_recover = 0 # Zera a perda acumulada
            self.current_martingale_level = 0
            self.accumulated_loss_cycle = 0.0
            # No modo agressivo, um win em qualquer ciclo reseta tudo para o Ciclo 1
            self.current_cycle = 1

        else:
            # LOSS
            self.accumulated_loss_cycle += entry_value
            self.current_martingale_level += 1
            self.log_callback(f"LOSS no Ciclo {self.current_cycle} (Gale {self.current_martingale_level-1}). Acumulado no ciclo: {self.accumulated_loss_cycle:.2f}", "LOSS")

            if self.current_martingale_level > self.martingale_levels:
                # Fim de um ciclo
                self.log_callback(f"Ciclo {self.current_cycle} finalizado com perda.", "AVISO")
                self.total_loss_to_recover = self.accumulated_loss_cycle
                self.current_cycle += 1
                self.current_martingale_level = 0
                self.accumulated_loss_cycle = 0.0

                if self.current_cycle > self.max_cycles:
                    self.log_callback(f"Número máximo de ciclos ({self.max_cycles}) atingido. Gerenciamento pausado.", "STOP")
                    self.is_active = False
