# bot/management/masaniello_manager.py

import math
import logging

class MasanielloManager:
    """
    Calcula a progressão da estratégia de gerenciamento de capital Masaniello.
    """
    def __init__(self, capital, num_trades, expected_wins, payout):
        self.capital_inicial = float(capital)
        self.N = int(num_trades)
        self.K = int(expected_wins)
        self.payout = float(payout) / 100.0
        
        self.eventos_totais = self.N
        self.eventos_favoraveis = self.K
        self.caixa_atual = self.capital_inicial
        
        self.operacoes_realizadas = 0
        self.wins_atuais = 0
        self.losses_atuais = 0
        self.status = "Aguardando Início"

        logging.info(f"Masaniello inicializado: Capital={capital}, N={self.N}, K={self.K}, Payout={self.payout}")

    def _combinacao(self, n, k):
        """Calcula o número de combinações (n escolhe k)."""
        if k < 0 or k > n:
            return 0
        return math.factorial(n) // (math.factorial(k) * math.factorial(n - k))

    def _calcula_quantia_apostar(self):
        """
        Fórmula principal do Masaniello para determinar o valor da próxima aposta.
        """
        numerador = self._combinacao(self.eventos_totais - 1, self.eventos_favoraveis)
        denominador = self._combinacao(self.eventos_totais, self.eventos_favoraveis)
        
        if denominador == 0:
            logging.error("Masaniello: Denominador zero no cálculo da fração. Impossível continuar.")
            self.status = "Erro de Cálculo"
            return 0

        fracao = numerador / denominador
        
        quantia = (self.caixa_atual * (1 - fracao)) / self.payout
        return round(quantia, 2)

    def get_next_entry_value(self):
        """
        Retorna o valor da próxima entrada. Retorna 0 se o ciclo terminou ou deu erro.
        """
        if self.operacoes_realizadas >= self.N:
            self.status = "Ciclo Concluído"
            logging.info("Masaniello: Ciclo concluído (Nº de trades atingido).")
            return 0
            
        if self.wins_atuais >= self.K:
            self.status = "Meta de Wins Atingida"
            logging.info("Masaniello: Meta de vitórias atingida.")
            return 0

        if (self.N - self.operacoes_realizadas) == (self.K - self.wins_atuais):
             # Força a aposta do saldo restante se o número de trades restantes for igual ao número de wins necessários
            logging.info("Masaniello: All-in forçado para atingir a meta.")
            return round(self.caixa_atual / self.payout, 2)
            
        valor_aposta = self._calcula_quantia_apostar()

        if self.caixa_atual <= 0 or valor_aposta <= 0:
            self.status = "Ciclo Quebrado"
            logging.warning("Masaniello: Caixa zerado ou aposta negativa. Ciclo quebrado.")
            return 0
            
        self.status = "Em Operação"
        return valor_aposta

    def record_trade(self, entry_value, profit):
        """
        Registra o resultado de uma operação e atualiza o estado do ciclo.
        """
        self.operacoes_realizadas += 1
        
        if profit > 0:
            self.wins_atuais += 1
            self.caixa_atual += profit
            self.eventos_favoraveis -= 1
        else:
            self.losses_atuais += 1
            self.caixa_atual -= entry_value
            
        self.eventos_totais -= 1
        
        logging.info(f"Masaniello Pós-Trade: Wins={self.wins_atuais}, Losses={self.losses_atuais}, Caixa={self.caixa_atual:.2f}")

    def get_summary(self):
        """Retorna um resumo do estado atual do ciclo."""
        return {
            "caixa_atual": self.caixa_atual,
            "operacoes_realizadas": self.operacoes_realizadas,
            "wins": self.wins_atuais,
            "losses": self.losses_atuais,
            "status": self.status
        }

    def get_status(self):
        """
        Retorna um dicionário com o estado atual do ciclo Masaniello.
        Esta função serve como um "painel de informações" para a interface gráfica.
        """
        is_finished = self.status not in ["Aguardando Início", "Em Operação"]
        return {
            'current_trade': self.operacoes_realizadas,
            'num_trades': self.N,
            'wins_so_far': self.wins_atuais,
            'expected_wins': self.K,
            'current_capital': self.caixa_atual,
            'is_finished': is_finished,
            'result_message': self.status
        }