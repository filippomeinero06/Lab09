from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO

class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()

        for r in relazioni:     # relazioni è una lista di dizionari [{"id_escur": 1, "id_p_int": 3}, {...}]
            id_escurione = r["id_escursione"]
            id_punto_interesse = r["id_punto_interesse"]

            for escursione in self.escursioni_map:
                if escursione.id == id_escurione:
                    escursione.punti_interesse.add(id_punto_interesse)

            for punto_interesse in self.punti_interesse_map:
                if punto_interesse.id == id_punto_interesse:
                    punto_interesse.escursioni.add(id_escurione)



    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        self._ricorsione(0, [], 0, self._costo, 0, set(), id_parco, max_giorni, max_budget)

        if self._valore_ottimo == -1:
            return [], 0, 0

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set, id_parco, max_giorni, max_budget):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        if self.escursione_rispetta_limiti(durata_corrente, costo_corrente, max_giorni, max_budget):
            if self._valore_ottimo == -1 or valore_corrente > self._valore_ottimo:
                self._pacchetto_ottimo = pacchetto_parziale.copy()
                self._valore_ottimo = valore_corrente
            return
        else:
            for _, escursione in self.escursioni_map.items():
                somma_voti = 0
                if escursione.id_parco == id_parco:
                    for punto in escursione.punti_interesse:
                        if punto not in punti_usati:
                            somma_voti += self.punti_interesse_map[punto].voto_visitatori
                            punti_usati.add(punto)

                    if valore_corrente + somma_voti > self._valore_ottimo and self.escursione_valida(pacchetto_parziale, escursione):
                        valore_corrente += somma_voti
                        pacchetto_parziale.append(escursione.id)
                        self._ricorsione(start_index, pacchetto_parziale, durata_corrente, costo_corrente, valore_corrente, punti_usati, id_parco, max_giorni, max_budget)
                        punti_usati.clear()
                        pacchetto_parziale.pop()

    @staticmethod
    def escursione_valida(pacchetto_parziale, escursione):
        # 1) Le escursioni incluse nel pacchetto devono essere tutte diverse tra loro.
        for esc in pacchetto_parziale:
            if esc == escursione.id:
                return False
        return True

    @staticmethod
    def escursione_rispetta_limiti(durata_corrente, costo_corrente, max_giorni, max_budget):
        if max_giorni is not None and max_budget is not None and durata_corrente >= max_giorni or costo_corrente >= max_budget:
            return False
        elif max_giorni is None and max_budget is not None and costo_corrente >= max_budget:
            return False
        elif max_giorni is not None and max_budget is None and durata_corrente >= max_giorni:
            return False
        else:
            return True






if __name__ == '__main__':

    m = Model()
