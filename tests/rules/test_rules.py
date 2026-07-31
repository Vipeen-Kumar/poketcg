"""Unit tests for the Pokémon rule library."""

from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.actions import (
    ActionBatch,
    ActionKind,
    AbilityAction,
    AttackAction,
    AttachEnergyAction,
    BaseAction,
    EndTurnAction,
    EvolutionAction,
    PlayCardAction,
    RetreatAction,
)
from poketcg.analysis import GameAnalyzer
from poketcg.cards import CardDatabase
from poketcg.cards.models import CardData
from poketcg.decision import DecisionContext, DecisionEngine, DecisionEngineConfig, RuleRegistry
from poketcg.domain import (
    Bench,
    Card,
    EffectContext,
    GamePhase,
    GameState,
    Observation,
    OptionReference,
    OptionType,
    Player,
    PlayerSide,
    Pokemon,
    PrizeCards,
    SelectContext,
    SelectPrompt,
    SelectType,
    Zone,
)
from poketcg.rules import (
    AbilityRule,
    AttackRule,
    AttachEnergyRule,
    EndTurnRule,
    EvolutionRule,
    FallbackRule,
    ItemRule,
    RetreatRule,
    StadiumRule,
    SupporterRule,
)


class RuleLibraryTestCase(unittest.TestCase):
    """Tests for individual Pokémon rules and their engine integration."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.card_database = CardDatabase()
        cls.card_database.load()

    def test_attack_rule_available(self) -> None:
        analyzer, context, action = self._build_attack_context()
        result = AttackRule().evaluate(context)

        self.assertTrue(result.passed)
        self.assertIs(result.selected_action, action)
        self.assertIn("energy", result.reason.lower())

    def test_attack_rule_unavailable(self) -> None:
        analyzer, context, _ = self._build_attack_context(include_attack=False)
        result = AttackRule().evaluate(context)

        self.assertFalse(result.passed)
        self.assertIsNone(result.selected_action)
        self.assertEqual(result.reason, "No attack action available.")

    def test_attach_energy_rule_available(self) -> None:
        analyzer, context, action = self._build_energy_context()
        result = AttachEnergyRule().evaluate(context)

        self.assertTrue(result.passed)
        self.assertIs(result.selected_action, action)
        self.assertIn("unused", result.reason.lower())

    def test_attach_energy_rule_unavailable(self) -> None:
        analyzer, context, _ = self._build_energy_context(include_energy=False)
        result = AttachEnergyRule().evaluate(context)

        self.assertFalse(result.passed)
        self.assertIsNone(result.selected_action)
        self.assertEqual(result.reason, "No attachable energy.")

    def test_retreat_rule_available(self) -> None:
        analyzer, context, action = self._build_retreat_context()
        result = RetreatRule().evaluate(context)

        self.assertTrue(result.passed)
        self.assertIs(result.selected_action, action)

    def test_retreat_rule_unavailable(self) -> None:
        analyzer, context, _ = self._build_retreat_context(include_retreat=False)
        result = RetreatRule().evaluate(context)

        self.assertFalse(result.passed)
        self.assertIsNone(result.selected_action)
        self.assertEqual(result.reason, "No retreat action available.")

    def test_evolution_rule_available(self) -> None:
        analyzer, context, action = self._build_evolution_context()
        result = EvolutionRule().evaluate(context)

        self.assertTrue(result.passed)
        self.assertIs(result.selected_action, action)

    def test_evolution_rule_unavailable(self) -> None:
        analyzer, context, _ = self._build_evolution_context(include_evolution=False)
        result = EvolutionRule().evaluate(context)

        self.assertFalse(result.passed)
        self.assertIsNone(result.selected_action)
        self.assertEqual(result.reason, "No evolution action available.")

    def test_supporter_rule_available(self) -> None:
        analyzer, context, action = self._build_play_context("supporter")
        result = SupporterRule().evaluate(context)

        self.assertTrue(result.passed)
        self.assertIs(result.selected_action, action)

    def test_supporter_rule_unavailable(self) -> None:
        analyzer, context, _ = self._build_play_context("supporter", include_action=False)
        result = SupporterRule().evaluate(context)

        self.assertFalse(result.passed)
        self.assertIsNone(result.selected_action)
        self.assertEqual(result.reason, "No supporter action available.")

    def test_item_rule_available(self) -> None:
        analyzer, context, action = self._build_play_context("item")
        result = ItemRule().evaluate(context)

        self.assertTrue(result.passed)
        self.assertIs(result.selected_action, action)

    def test_item_rule_unavailable(self) -> None:
        analyzer, context, _ = self._build_play_context("item", include_action=False)
        result = ItemRule().evaluate(context)

        self.assertFalse(result.passed)
        self.assertIsNone(result.selected_action)
        self.assertEqual(result.reason, "No item action available.")

    def test_ability_rule_available(self) -> None:
        analyzer, context, action = self._build_ability_context()
        result = AbilityRule().evaluate(context)

        self.assertTrue(result.passed)
        self.assertIs(result.selected_action, action)

    def test_ability_rule_unavailable(self) -> None:
        analyzer, context, _ = self._build_ability_context(include_action=False)
        result = AbilityRule().evaluate(context)

        self.assertFalse(result.passed)
        self.assertIsNone(result.selected_action)
        self.assertEqual(result.reason, "No ability action available.")

    def test_stadium_rule_available(self) -> None:
        analyzer, context, action = self._build_play_context("stadium")
        result = StadiumRule().evaluate(context)

        self.assertTrue(result.passed)
        self.assertIs(result.selected_action, action)

    def test_stadium_rule_unavailable(self) -> None:
        analyzer, context, _ = self._build_play_context("stadium", include_action=False)
        result = StadiumRule().evaluate(context)

        self.assertFalse(result.passed)
        self.assertIsNone(result.selected_action)
        self.assertEqual(result.reason, "No stadium action available.")

    def test_end_turn_rule(self) -> None:
        analyzer, context, action = self._build_end_turn_context()
        result = EndTurnRule().evaluate(context)

        self.assertTrue(result.passed)
        self.assertIs(result.selected_action, action)
        self.assertEqual(result.reason, "End turn is legal.")

    def test_fallback_rule_prefers_end_turn(self) -> None:
        analyzer, context, action = self._build_end_turn_context()
        result = FallbackRule().evaluate(context)

        self.assertTrue(result.passed)
        self.assertIs(result.selected_action, action)
        self.assertEqual(result.reason, "Fallback selected End Turn.")

    def test_registry_priority_and_disable(self) -> None:
        attack_rule = AttackRule()
        end_turn_rule = EndTurnRule()
        fallback_rule = FallbackRule()
        registry = RuleRegistry([attack_rule, end_turn_rule, fallback_rule])

        ordered_names = [rule.name for rule in registry.ordered_rules()]
        self.assertEqual(ordered_names[:2], ["AttackRule", "EndTurnRule"])

        attack_rule.disable()
        self.assertFalse(attack_rule.enabled)
        self.assertEqual([rule.name for rule in registry.ordered_rules()], ["EndTurnRule"])

    def test_engine_uses_disabled_rule_configuration(self) -> None:
        analyzer, context, attack_action = self._build_attack_context()
        end_turn_action = self._make_end_turn_action()
        combined_analyzer = self._build_analyzer(analyzer.state, (attack_action, end_turn_action))
        rules = [AttackRule(), EndTurnRule(), FallbackRule()]
        registry = RuleRegistry(rules)
        context = DecisionContext(
            analyzer=combined_analyzer,
            legal_actions=(attack_action, end_turn_action),
            config=DecisionEngineConfig(disabled_rules=("AttackRule",)),
        )

        chosen_action = DecisionEngine(registry=registry).choose_action(context)

        self.assertIs(chosen_action, end_turn_action)

    def test_replay_trace_consumes_rule_result(self) -> None:
        temp_dir = self._make_temp_dir()
        try:
            from poketcg.debug import ReplayLogger
            from poketcg.debug.replay_logger import ReplayLoggerConfig

            analyzer, context, action = self._build_end_turn_context()
            logger = ReplayLogger(
                ReplayLoggerConfig(
                    enabled=True,
                    output_directory=temp_dir,
                    markdown=True,
                    json=True,
                    maximum_saved_games=10,
                )
            )
            logger.start_game("rule_001")

            decision_context = DecisionContext(
                analyzer=analyzer,
                replay_logger=logger,
                config=DecisionEngineConfig(logging_enabled=True),
            )
            registry = RuleRegistry([EndTurnRule(), FallbackRule()])
            chosen_action = DecisionEngine(registry=registry).choose_action(decision_context)

            self.assertIs(chosen_action, action)
            snapshot = logger.session.turns[0]
            self.assertIsNotNone(snapshot.decision_trace)
            self.assertEqual(snapshot.decision_trace["selected_rule_name"], "EndTurnRule")
            self.assertIsNotNone(logger.session.turns[0].decision_metadata.rule_name)
            finished = logger.finish()
            self.assertIsNotNone(finished.json_path)
            self.assertIsNotNone(finished.markdown_path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _build_attack_context(self, include_attack: bool = True) -> tuple[GameAnalyzer, DecisionContext, BaseAction | None]:
        active_card = self._pokemon_card(require_attack=True)
        active = self._pokemon(active_card)
        state = self._state(active)
        actions: tuple[BaseAction, ...] = ()
        selected_action: BaseAction | None = None
        if include_attack:
            attack = active_card.attacks[0]
            selected_action = self._make_attack_action(active, attack)
            actions = (selected_action,)
        else:
            actions = (self._make_end_turn_action(),)
        analyzer = self._build_analyzer(state, actions)
        return analyzer, DecisionContext(analyzer=analyzer), selected_action

    def _build_energy_context(self, include_energy: bool = True) -> tuple[GameAnalyzer, DecisionContext, BaseAction | None]:
        active_card = self._pokemon_card(require_attack=True)
        active = self._pokemon(active_card)
        state = self._state(active)
        if include_energy:
            energy_card = self._card_by_type("BASIC_ENERGY")
            action = self._make_attach_energy_action(active, energy_card)
            actions: tuple[BaseAction, ...] = (action,)
        else:
            action = None
            actions = (self._make_end_turn_action(),)
        analyzer = self._build_analyzer(state, actions)
        return analyzer, DecisionContext(analyzer=analyzer), action

    def _build_retreat_context(self, include_retreat: bool = True) -> tuple[GameAnalyzer, DecisionContext, BaseAction | None]:
        active_card = self._pokemon_card(require_attack=True)
        active = self._pokemon(active_card)
        bench_card = self._pokemon_card()
        bench = self._pokemon(bench_card)
        state = self._state(active, bench=bench)
        if include_retreat:
            action = self._make_retreat_action(bench)
            actions: tuple[BaseAction, ...] = (action,)
        else:
            action = None
            actions = (self._make_end_turn_action(),)
        analyzer = self._build_analyzer(state, actions)
        return analyzer, DecisionContext(analyzer=analyzer), action

    def _build_evolution_context(self, include_evolution: bool = True) -> tuple[GameAnalyzer, DecisionContext, BaseAction | None]:
        base_card, evolve_card = self._evolution_pair()
        active = self._pokemon(base_card)
        state = self._state(active)
        if include_evolution:
            action = self._make_evolution_action(active, evolve_card)
            actions: tuple[BaseAction, ...] = (action,)
        else:
            action = None
            actions = (self._make_end_turn_action(),)
        analyzer = self._build_analyzer(state, actions)
        return analyzer, DecisionContext(analyzer=analyzer), action

    def _build_play_context(self, category: str, include_action: bool = True) -> tuple[GameAnalyzer, DecisionContext, BaseAction | None]:
        active_card = self._pokemon_card(require_attack=True)
        active = self._pokemon(active_card)
        state = self._state(active)
        if category == "supporter":
            card = self._card_by_type("SUPPORTER")
            action = self._make_play_action(card, category)
            state.supporter_played = False
        elif category == "item":
            card = self._card_by_type("ITEM")
            action = self._make_play_action(card, category)
        elif category == "stadium":
            card = self._card_by_type("STADIUM")
            action = self._make_play_action(card, category)
            state.stadium_played = False
        else:
            raise AssertionError(f"Unsupported category: {category}")

        actions: tuple[BaseAction, ...]
        if include_action:
            actions = (action,)
        else:
            action = None
            actions = (self._make_end_turn_action(),)
        analyzer = self._build_analyzer(state, actions)
        return analyzer, DecisionContext(analyzer=analyzer), action

    def _build_ability_context(self, include_action: bool = True) -> tuple[GameAnalyzer, DecisionContext, BaseAction | None]:
        ability_card = self._pokemon_card(require_ability=True)
        active = self._pokemon(ability_card)
        state = self._state(active)
        if include_action:
            ability = next(ability for ability in ability_card.abilities if ability.kind == "ability")
            action = self._make_ability_action(active, ability)
            actions: tuple[BaseAction, ...] = (action,)
        else:
            action = None
            actions = (self._make_end_turn_action(),)
        analyzer = self._build_analyzer(state, actions)
        return analyzer, DecisionContext(analyzer=analyzer), action

    def _build_end_turn_context(self) -> tuple[GameAnalyzer, DecisionContext, BaseAction]:
        active_card = self._pokemon_card(require_attack=True)
        active = self._pokemon(active_card)
        state = self._state(active)
        action = self._make_end_turn_action()
        analyzer = self._build_analyzer(state, (action,))
        return analyzer, DecisionContext(analyzer=analyzer), action

    def _build_analyzer(self, state: GameState, actions: tuple[BaseAction, ...]) -> GameAnalyzer:
        observation = Observation(state=state, logs=(), selection=self._selection())
        batch = ActionBatch(state=state, selection_context=SelectContext.MAIN, selection_type=SelectType.MAIN, actions=actions)
        return GameAnalyzer(observation, actions=batch)

    def _selection(self) -> SelectPrompt:
        return SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.MAIN,
            min_count=1,
            max_count=1,
            options=(OptionReference(option_type=OptionType.END),),
            effect_context=EffectContext(),
        )

    def _state(
        self,
        active: Pokemon,
        *,
        bench: Pokemon | None = None,
        supporter_played: bool = False,
        stadium_played: bool = False,
        energy_attached: bool = False,
    ) -> GameState:
        me = Player(
            player_index=0,
            side=PlayerSide.SELF,
            active=active,
            bench=Bench(pokemon=() if bench is None else (bench,)),
            hand=(),
            deck_count=30,
            discard=(),
            prizes=PrizeCards(),
        )
        opponent_card = self._pokemon_card()
        opponent = Player(
            player_index=1,
            side=PlayerSide.OPPONENT,
            active=self._pokemon(opponent_card),
            bench=Bench(),
            hand=None,
            deck_count=30,
            discard=(),
            prizes=PrizeCards(),
        )
        return GameState(
            turn=1,
            phase=GamePhase.MAIN,
            current_player=PlayerSide.SELF,
            first_player=PlayerSide.SELF,
            players=(me, opponent),
            supporter_played=supporter_played,
            stadium_played=stadium_played,
            energy_attached=energy_attached,
        )

    def _pokemon(self, card_data: CardData) -> Pokemon:
        card = Card(metadata=card_data)
        hp = card_data.hp or 10
        return Pokemon(card=card, current_hp=hp, max_hp=hp)

    def _pokemon_card(self, *, require_attack: bool = False, require_ability: bool = False) -> CardData:
        for card in self.card_database.by_type(self._card_type("POKEMON")):
            if require_attack and not card.attacks:
                continue
            if require_ability and not any(ability.kind == "ability" for ability in card.abilities):
                continue
            return card
        raise AssertionError("No matching Pokémon card found.")

    def _evolution_card(self, base_name: str) -> CardData:
        matches = self.card_database.by_evolves_from(base_name)
        if not matches:
            raise AssertionError(f"No evolution card found for {base_name!r}.")
        return matches[0]

    def _evolution_pair(self) -> tuple[CardData, CardData]:
        for candidate in self.card_database.by_type(self._card_type("POKEMON")):
            matches = self.card_database.by_evolves_from(candidate.name)
            if matches:
                return candidate, matches[0]
        raise AssertionError("No evolution pair found in the card database.")

    def _card_by_type(self, card_type_name: str) -> CardData:
        return self.card_database.by_type(self._card_type(card_type_name))[0]

    def _card_type(self, card_type_name: str):
        from poketcg.domain import CardType

        return getattr(CardType, card_type_name)

    def _make_attack_action(self, pokemon: Pokemon, attack) -> AttackAction:
        return AttackAction(
            action_index=0,
            kind=ActionKind.ATTACK,
            option=OptionReference(option_type=OptionType.ATTACK, attack_id=0),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.ATTACK,
            attacker=pokemon,
            attack_id=0,
            attack_name=attack.name,
            attack=attack,
            energy_cost=attack.cost.symbols,
            damage=attack.damage,
        )

    def _make_attach_energy_action(self, target: Pokemon, card_data: CardData) -> AttachEnergyAction:
        return AttachEnergyAction(
            action_index=0,
            kind=ActionKind.ATTACH_ENERGY,
            option=OptionReference(option_type=OptionType.ATTACH, card=Card(metadata=card_data)),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
            card=Card(metadata=card_data),
            source_zone=Zone.HAND,
            source_index=0,
            target_zone=Zone.ACTIVE,
            target_index=0,
            target_owner=PlayerSide.SELF,
            target_pokemon=target,
        )

    def _make_retreat_action(self, target: Pokemon) -> RetreatAction:
        return RetreatAction(
            action_index=0,
            kind=ActionKind.RETREAT,
            option=OptionReference(option_type=OptionType.RETREAT),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
            target_zone=Zone.BENCH,
            target_index=0,
            target_owner=PlayerSide.SELF,
            target_pokemon=target,
        )

    def _make_evolution_action(self, target: Pokemon, card_data: CardData) -> EvolutionAction:
        card = Card(metadata=card_data)
        return EvolutionAction(
            action_index=0,
            kind=ActionKind.EVOLVE,
            option=OptionReference(option_type=OptionType.EVOLVE, card=card),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.EVOLVE,
            evolution_card=card,
            target_zone=Zone.ACTIVE,
            target_index=0,
            target_owner=PlayerSide.SELF,
            target_pokemon=target,
        )

    def _make_play_action(self, card_data: CardData, category: str) -> PlayCardAction:
        card = Card(metadata=card_data)
        option_type = OptionType.PLAY
        return PlayCardAction(
            action_index=0,
            kind=ActionKind.PLAY_CARD,
            option=OptionReference(option_type=option_type, card=card),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
            card=card,
            source_zone=Zone.HAND,
            source_index=0,
        )

    def _make_ability_action(self, source: Pokemon, ability) -> AbilityAction:
        return AbilityAction(
            action_index=0,
            kind=ActionKind.USE_ABILITY,
            option=OptionReference(option_type=OptionType.SKILL),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
            source_pokemon=source,
            ability_name=ability.name,
            ability=ability,
        )

    def _make_end_turn_action(self) -> EndTurnAction:
        return EndTurnAction(
            action_index=0,
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )

    def _make_temp_dir(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        path = TMP_ROOT / f"rules_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=True)
        return path


if __name__ == "__main__":
    unittest.main()
