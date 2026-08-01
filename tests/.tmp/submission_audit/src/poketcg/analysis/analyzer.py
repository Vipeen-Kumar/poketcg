"""Reusable factual analysis over parsed game state and typed actions."""

from __future__ import annotations

from typing import cast

from poketcg.actions import (
    AbilityAction,
    ActionBatch,
    ActionFactory,
    AttachEnergyAction,
    AttackAction,
    BaseAction,
    EndTurnAction,
    EnergyChoiceAction,
    EvolutionAction,
    PlayCardAction,
    RetreatAction,
)
from poketcg.cards.models import AttackData
from poketcg.domain import Card, GameState, Observation, Player, PlayerSide, Pokemon, PokemonType, StatusCondition


class GameAnalyzer:
    """Answer factual questions about a parsed observation."""

    def __init__(
        self,
        observation: Observation,
        *,
        actions: ActionBatch | None = None,
        action_factory: ActionFactory | None = None,
    ) -> None:
        self._observation = observation
        self._action_batch = actions
        self._action_factory = action_factory or ActionFactory()
        self._cache: dict[tuple[object, ...], object] = {}

    @property
    def observation(self) -> Observation:
        """Return the parsed observation being analyzed."""

        return self._observation

    @property
    def state(self) -> GameState | None:
        """Return the parsed game state."""

        return self._observation.state

    def is_terminal(self) -> bool:
        """Return whether the game is in a terminal state."""

        return self._observation.is_terminal

    def current_turn(self) -> int | None:
        """Return the absolute turn number."""

        return self._observation.turn

    def current_player(self) -> PlayerSide | None:
        """Return the player whose turn it is."""

        if self.state is None:
            return None
        return self.state.current_player

    def first_player(self) -> PlayerSide | None:
        """Return which side went first."""

        if self.state is None:
            return None
        return self.state.first_player

    def me(self) -> Player | None:
        """Return the perspective player."""

        return self._observation.me

    def opponent(self) -> Player | None:
        """Return the opponent player."""

        return self._observation.opponent

    def active(self, player: Player | PlayerSide | None = None) -> Pokemon | None:
        """Return the active Pokemon for the requested side."""

        resolved = self._resolve_player(player)
        return None if resolved is None else resolved.active

    def bench(self, player: Player | PlayerSide | None = None) -> tuple[Pokemon | None, ...]:
        """Return the bench slots for the requested side."""

        resolved = self._resolve_player(player)
        if resolved is None:
            return ()
        return resolved.bench.pokemon

    def hand(self, player: Player | PlayerSide | None = None) -> tuple[Card, ...]:
        """Return visible hand cards for the requested side."""

        resolved = self._resolve_player(player)
        if resolved is None or resolved.hand is None:
            return ()
        return resolved.hand

    def deck_size(self, player: Player | PlayerSide | None = None) -> int:
        """Return remaining deck size for the requested side."""

        resolved = self._resolve_player(player)
        return 0 if resolved is None else resolved.deck_count

    def discard(self, player: Player | PlayerSide | None = None) -> tuple[Card, ...]:
        """Return discard-pile cards for the requested side."""

        resolved = self._resolve_player(player)
        return () if resolved is None else resolved.discard

    def prizes_remaining(self, player: Player | PlayerSide | None = None) -> int:
        """Return the number of prize cards remaining."""

        resolved = self._resolve_player(player)
        if resolved is None:
            return 0
        return resolved.prizes.remaining

    def bench_space(self, player: Player | PlayerSide | None = None) -> int:
        """Return remaining open bench slots."""

        resolved = self._resolve_player(player)
        if resolved is None:
            return 0
        return max(resolved.bench.max_size - self._occupied_bench_count(resolved), 0)

    def has_empty_bench_slot(self, player: Player | PlayerSide | None = None) -> bool:
        """Return whether the requested side has at least one open bench slot."""

        return self.bench_space(player) > 0

    def can_attack(self, pokemon: Pokemon | None = None) -> bool:
        """Return whether a matching attack action currently exists."""

        target = pokemon or self.active()
        if target is None:
            return False
        return any(action.attacker == target or (action.attacker is None and target == self.active()) for action in self.attack_actions())

    def can_retreat(self, player: Player | PlayerSide | None = None) -> bool:
        """Return whether a retreat action currently exists."""

        resolved = self._resolve_player(player)
        active = None if resolved is None else resolved.active
        if active is None:
            return False
        return any(action.target_pokemon is None or action.target_pokemon != active for action in self.retreat_actions())

    def can_evolve(self, pokemon: Pokemon | None = None) -> bool:
        """Return whether a matching evolution action currently exists."""

        target = pokemon or self.active()
        if target is None:
            return False
        return any(action.target_pokemon == target for action in self.evolution_actions())

    def damage_taken(self, pokemon: Pokemon | None = None) -> int:
        """Return total damage currently on a Pokemon."""

        target = pokemon or self.active()
        if target is None:
            return 0
        return max(target.max_hp - target.current_hp, 0)

    def hp_remaining(self, pokemon: Pokemon | None = None) -> int:
        """Return current HP for a Pokemon."""

        target = pokemon or self.active()
        return 0 if target is None else target.current_hp

    def has_energy(self, pokemon: Pokemon | None = None) -> bool:
        """Return whether a Pokemon has any attached energy."""

        target = pokemon or self.active()
        if target is None:
            return False
        return self.energy_count(target) > 0

    def energy_count(self, subject: Player | PlayerSide | Pokemon | None = None) -> int:
        """Return attached-energy count for a Pokemon or board-side total."""

        if isinstance(subject, Pokemon):
            return max(len(subject.attached_energy_cards), len(subject.attached_energy_types))
        resolved = self._resolve_player(subject)
        if resolved is None:
            return 0
        return sum(self.energy_count(pokemon) for pokemon in self._in_play_pokemon(resolved))

    def has_tool(self, subject: Player | PlayerSide | Pokemon | None = None) -> bool:
        """Return whether a Pokemon has a tool or a hand contains a tool."""

        if isinstance(subject, Pokemon):
            return bool(subject.attached_tools)
        return self.tool_count(subject) > 0

    def is_knocked_out(self, pokemon: Pokemon | None = None) -> bool:
        """Return whether a Pokemon has zero or less HP remaining."""

        target = pokemon or self.active()
        if target is None:
            return False
        return target.current_hp <= 0

    def has_status_condition(self, subject: Player | Pokemon | None = None, condition: StatusCondition | None = None) -> bool:
        """Return whether a player or Pokemon has any or a specific status condition."""

        conditions = self._status_conditions(subject)
        if condition is None:
            return bool(conditions)
        return condition in conditions

    def available_attacks(self, pokemon: Pokemon | None = None) -> tuple[AttackData, ...]:
        """Return static attacks for a Pokemon."""

        target = pokemon or self.active()
        if target is None:
            return ()
        return target.card.metadata.attacks

    def attack_cost(self, attack: AttackData | str | int, pokemon: Pokemon | None = None) -> tuple[PokemonType, ...]:
        """Return the energy cost symbols for an attack."""

        resolved = self._resolve_attack(attack, pokemon)
        return () if resolved is None else resolved.cost.symbols

    def attack_damage(self, attack: AttackData | str | int, pokemon: Pokemon | None = None) -> str | None:
        """Return the printed damage field for an attack."""

        resolved = self._resolve_attack(attack, pokemon)
        return None if resolved is None else resolved.damage

    def attack_names(self, pokemon: Pokemon | None = None) -> tuple[str, ...]:
        """Return attack names for a Pokemon."""

        return tuple(attack.name for attack in self.available_attacks(pokemon))

    def attack_count(self, pokemon: Pokemon | None = None) -> int:
        """Return the number of attacks a Pokemon has."""

        return len(self.available_attacks(pokemon))

    def has_supporter(self, player: Player | PlayerSide | None = None) -> bool:
        """Return whether the visible hand contains a Supporter."""

        return any(card.metadata.is_supporter() for card in self.hand(player))

    def has_item(self, player: Player | PlayerSide | None = None) -> bool:
        """Return whether the visible hand contains an Item."""

        return any(card.metadata.is_item() for card in self.hand(player))

    def has_stadium(self, player: Player | PlayerSide | None = None) -> bool:
        """Return whether the visible hand contains a Stadium."""

        return any(card.metadata.is_stadium() for card in self.hand(player))

    def basic_pokemon_in_hand(self, player: Player | PlayerSide | None = None) -> tuple[Card, ...]:
        """Return visible Basic Pokemon in hand."""

        return tuple(card for card in self.hand(player) if card.metadata.is_pokemon() and card.metadata.is_basic())

    def energy_cards_in_hand(self, player: Player | PlayerSide | None = None) -> tuple[Card, ...]:
        """Return visible Energy cards in hand."""

        return tuple(card for card in self.hand(player) if card.metadata.is_energy())

    def search_cards(self, keyword: str, player: Player | PlayerSide | None = None) -> tuple[Card, ...]:
        """Return visible hand cards matching a case-insensitive keyword."""

        needle = keyword.casefold()
        matches: list[Card] = []
        for card in self.hand(player):
            haystacks = [card.name, card.metadata.effect_text or "", card.metadata.rule or "", card.metadata.category or ""]
            if any(needle in text.casefold() for text in haystacks):
                matches.append(card)
        return tuple(matches)

    def active_pokemon(self, player: Player | PlayerSide | None = None) -> Pokemon | None:
        """Return the active Pokemon for the requested side."""

        return self.active(player)

    def bench_pokemon(self, player: Player | PlayerSide | None = None) -> tuple[Pokemon, ...]:
        """Return occupied bench Pokemon slots only."""

        return tuple(pokemon for pokemon in self.bench(player) if pokemon is not None)

    def total_energy(self, player: Player | PlayerSide | None = None) -> int:
        """Return total attached energy cards across the in-play board."""

        return self.energy_count(player)

    def total_hp(self, player: Player | PlayerSide | None = None) -> int:
        """Return total current HP across in-play Pokemon."""

        resolved = self._resolve_player(player)
        if resolved is None:
            return 0
        return sum(pokemon.current_hp for pokemon in self._in_play_pokemon(resolved))

    def total_damage(self, player: Player | PlayerSide | None = None) -> int:
        """Return total damage across in-play Pokemon."""

        resolved = self._resolve_player(player)
        if resolved is None:
            return 0
        return sum(self.damage_taken(pokemon) for pokemon in self._in_play_pokemon(resolved))

    def total_prizes(self, player: Player | PlayerSide | None = None) -> int:
        """Return remaining prize count for the requested side."""

        return self.prizes_remaining(player)

    def actions(self) -> tuple[BaseAction, ...]:
        """Return typed legal actions for the current observation."""

        if self._observation.selection is None:
            return ()
        return self._get_action_batch().actions

    def attack_actions(self) -> tuple[AttackAction, ...]:
        """Return all legal attack actions."""

        return self._filter_actions(AttackAction)

    def retreat_actions(self) -> tuple[RetreatAction, ...]:
        """Return all legal retreat actions."""

        return self._filter_actions(RetreatAction)

    def energy_actions(self) -> tuple[AttachEnergyAction | EnergyChoiceAction, ...]:
        """Return all legal energy-related actions."""

        return tuple(action for action in self.actions() if isinstance(action, (AttachEnergyAction, EnergyChoiceAction)))

    def play_actions(self) -> tuple[PlayCardAction, ...]:
        """Return all legal play-card actions."""

        return self._filter_actions(PlayCardAction)

    def end_turn_action(self) -> EndTurnAction | None:
        """Return the end-turn action if one is currently legal."""

        for action in self.actions():
            if isinstance(action, EndTurnAction):
                return action
        return None

    def evolution_actions(self) -> tuple[EvolutionAction, ...]:
        """Return all legal evolution actions."""

        return self._filter_actions(EvolutionAction)

    def ability_actions(self) -> tuple[AbilityAction, ...]:
        """Return all legal ability actions."""

        return self._filter_actions(AbilityAction)

    def is_poisoned(self, subject: Player | Pokemon | None = None) -> bool:
        """Return whether a player or Pokemon is poisoned."""

        return self.has_status_condition(subject, StatusCondition.POISONED)

    def is_asleep(self, subject: Player | Pokemon | None = None) -> bool:
        """Return whether a player or Pokemon is asleep."""

        return self.has_status_condition(subject, StatusCondition.ASLEEP)

    def is_paralyzed(self, subject: Player | Pokemon | None = None) -> bool:
        """Return whether a player or Pokemon is paralyzed."""

        return self.has_status_condition(subject, StatusCondition.PARALYZED)

    def has_special_condition(self, subject: Player | Pokemon | None = None) -> bool:
        """Return whether a player or Pokemon has any special condition."""

        return self.has_status_condition(subject)

    def pokemon_count(self, player: Player | PlayerSide | None = None) -> int:
        """Return the number of in-play Pokemon for a side."""

        resolved = self._resolve_player(player)
        if resolved is None:
            return 0
        return len(self._in_play_pokemon(resolved))

    def tool_count(self, subject: Player | PlayerSide | Pokemon | None = None) -> int:
        """Return attached-tool count for a Pokemon or tool-card count in hand for a side."""

        if isinstance(subject, Pokemon):
            return len(subject.attached_tools)
        return sum(1 for card in self.hand(subject) if card.metadata.is_tool())

    def supporter_count(self, player: Player | PlayerSide | None = None) -> int:
        """Return Supporter count in visible hand."""

        return sum(1 for card in self.hand(player) if card.metadata.is_supporter())

    def trainer_count(self, player: Player | PlayerSide | None = None) -> int:
        """Return Trainer card count in visible hand."""

        return sum(1 for card in self.hand(player) if card.metadata.is_trainer())

    def _get_action_batch(self) -> ActionBatch:
        """Return the cached typed action batch for the current selection."""

        if self._action_batch is not None:
            return self._action_batch
        self._action_batch = self._action_factory.from_observation(self._observation)
        return self._action_batch

    def _filter_actions(self, action_type: type[BaseAction]) -> tuple[BaseAction, ...]:
        cache_key = ("actions", action_type)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cast(tuple[BaseAction, ...], cached)
        filtered = tuple(action for action in self.actions() if isinstance(action, action_type))
        self._cache[cache_key] = filtered
        return filtered

    def _resolve_player(self, player: Player | PlayerSide | None) -> Player | None:
        if isinstance(player, Player):
            return player
        if self.state is None:
            return None
        if player is None or player is PlayerSide.SELF:
            return self.state.me
        if player is PlayerSide.OPPONENT:
            return self.state.opponent
        return None

    def _occupied_bench_count(self, player: Player) -> int:
        return sum(1 for pokemon in player.bench.pokemon if pokemon is not None)

    def _in_play_pokemon(self, player: Player) -> tuple[Pokemon, ...]:
        cache_key = ("in_play", player.side)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cast(tuple[Pokemon, ...], cached)
        pokemon: list[Pokemon] = []
        if player.active is not None:
            pokemon.append(player.active)
        pokemon.extend(slot for slot in player.bench.pokemon if slot is not None)
        result = tuple(pokemon)
        self._cache[cache_key] = result
        return result

    def _status_conditions(self, subject: Player | Pokemon | None) -> tuple[StatusCondition, ...]:
        if isinstance(subject, Pokemon):
            return subject.special_conditions
        if subject is None:
            player = self.me()
            return () if player is None else player.status_conditions
        return subject.status_conditions

    def _resolve_attack(self, attack: AttackData | str | int, pokemon: Pokemon | None) -> AttackData | None:
        attacks = self.available_attacks(pokemon)
        if isinstance(attack, AttackData):
            return attack if attack in attacks else None
        if isinstance(attack, int):
            if 0 <= attack < len(attacks):
                return attacks[attack]
            return None
        attack_name = attack.casefold()
        for candidate in attacks:
            if candidate.name.casefold() == attack_name:
                return candidate
        return None
