"""Unit tests for the action factory."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.actions import (
    AbilityAction,
    ActionFactory,
    ActionValidationError,
    ActionKind,
    AttackAction,
    AttachEnergyAction,
    CardChoiceAction,
    ChoiceAction,
    EndTurnAction,
    EnergyChoiceAction,
    EvolutionAction,
    PlayCardAction,
    RetreatAction,
    SpecialConditionChoiceAction,
    UnknownAction,
)
from poketcg.cards import CardDatabase
from poketcg.domain import Card, EffectContext, GameState, Observation, OptionReference, OptionType, Player, PlayerSide, Pokemon, SelectContext, SelectPrompt, SelectType, StatusCondition, Zone
from poketcg.engine import ObservationParser


class ActionFactoryTestCase(unittest.TestCase):
    """Tests for converting parsed legal options into typed actions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.card_database = CardDatabase()
        cls.card_database.load()

    def setUp(self) -> None:
        self.factory = ActionFactory()
        self.parser = ObservationParser(self.card_database)

    def test_from_observation_builds_batch(self) -> None:
        observation = self._build_observation()
        batch = self.factory.from_observation(observation)
        self.assertEqual(batch.selection_context, SelectContext.MAIN)
        self.assertEqual(batch.selection_type, SelectType.MAIN)
        self.assertEqual(len(batch.actions), 2)
        self.assertIsInstance(batch.actions[0], EndTurnAction)
        self.assertIsInstance(batch.actions[1], PlayCardAction)
        self.assertEqual(batch.actions[1].action_index, 1)

    def test_attack_action_maps_attack_metadata(self) -> None:
        observation = self._build_attack_observation()
        actions = self.factory.from_selection(observation.selection, state=observation.state)
        self.assertEqual(len(actions), 2)
        self.assertTrue(all(isinstance(action, AttackAction) for action in actions))
        self.assertEqual(actions[0].attack_name, "Nab 'n' Dash")
        self.assertEqual(actions[1].attack_name, "High Jump Kick")
        self.assertEqual(actions[1].damage, "100")

    def test_attach_action(self) -> None:
        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.MAIN,
            min_count=1,
            max_count=1,
            options=(
                OptionReference(
                    option_type=OptionType.ATTACH,
                    card=self._card(1, player_index=0),
                    zone=Zone.HAND,
                    zone_index=0,
                    owner=PlayerSide.SELF,
                    in_play_zone=Zone.BENCH,
                    in_play_index=0,
                ),
            ),
            effect_context=EffectContext(),
        )
        actions = self.factory.from_selection(selection, state=self._build_state())
        action = actions[0]
        self.assertIsInstance(action, AttachEnergyAction)
        self.assertEqual(action.card.name, "Basic {G} Energy")
        self.assertEqual(action.target_zone, Zone.BENCH)

    def test_evolution_action(self) -> None:
        selection = SelectPrompt(
            selection_type=SelectType.EVOLVE,
            context=SelectContext.EVOLVE,
            min_count=1,
            max_count=1,
            options=(
                OptionReference(
                    option_type=OptionType.EVOLVE,
                    card=self._card(21, player_index=0),
                    owner=PlayerSide.SELF,
                    in_play_zone=Zone.BENCH,
                    in_play_index=0,
                ),
            ),
            effect_context=EffectContext(),
        )
        action = self.factory.from_selection(selection, state=self._build_state())[0]
        self.assertIsInstance(action, EvolutionAction)
        self.assertEqual(action.evolution_card.name, "Scrafty")

    def test_ability_action(self) -> None:
        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.MAIN,
            min_count=1,
            max_count=1,
            options=(
                OptionReference(
                    option_type=OptionType.ABILITY,
                    owner=PlayerSide.SELF,
                    zone=Zone.ACTIVE,
                    zone_index=0,
                ),
            ),
            effect_context=EffectContext(),
        )
        state = self._build_state(active_card_id=28)
        action = self.factory.from_selection(selection, state=state)[0]
        self.assertIsInstance(action, AbilityAction)
        self.assertEqual(action.ability_name, "Storehouse Hideaway")

    def test_retreat_action(self) -> None:
        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.MAIN,
            min_count=1,
            max_count=1,
            options=(
                OptionReference(
                    option_type=OptionType.RETREAT,
                    owner=PlayerSide.SELF,
                    in_play_zone=Zone.BENCH,
                    in_play_index=0,
                ),
            ),
            effect_context=EffectContext(),
        )
        action = self.factory.from_selection(selection, state=self._build_state())[0]
        self.assertIsInstance(action, RetreatAction)
        self.assertEqual(action.target_zone, Zone.BENCH)

    def test_choice_mappings_cover_documented_option_types(self) -> None:
        cases = [
            (OptionType.NUMBER, ChoiceAction, ActionKind.CHOOSE_NUMBER, {"number": 2}),
            (OptionType.YES, ChoiceAction, ActionKind.CHOOSE_BOOLEAN, {}),
            (OptionType.NO, ChoiceAction, ActionKind.CHOOSE_BOOLEAN, {}),
            (OptionType.CARD, CardChoiceAction, ActionKind.CHOOSE_CARD, {"card": self._card(1, 0), "zone": Zone.HAND, "zone_index": 0}),
            (OptionType.TOOL_CARD, CardChoiceAction, ActionKind.CHOOSE_CARD, {"card": self._card(1154, 0), "zone": Zone.TOOL, "zone_index": 0}),
            (OptionType.ENERGY_CARD, CardChoiceAction, ActionKind.CHOOSE_CARD, {"card": self._card(1, 0), "zone": Zone.ENERGY, "zone_index": 0}),
            (OptionType.ENERGY, EnergyChoiceAction, ActionKind.CHOOSE_ENERGY, {"energy_count": 2}),
            (OptionType.DISCARD, CardChoiceAction, ActionKind.CHOOSE_CARD, {"card": self._card(1126, 0), "zone": Zone.DISCARD, "zone_index": 0}),
            (OptionType.SKILL, ChoiceAction, ActionKind.CHOOSE_SKILL, {"card": self._card(28, 0)}),
            (OptionType.SPECIAL_CONDITION, SpecialConditionChoiceAction, ActionKind.CHOOSE_SPECIAL_CONDITION, {"special_condition": StatusCondition.POISONED}),
            (OptionType.END, EndTurnAction, ActionKind.END_TURN, {}),
            (OptionType.PLAY, PlayCardAction, ActionKind.PLAY_CARD, {"card": self._card(1, 0), "zone": Zone.HAND, "zone_index": 0}),
        ]

        for option_type, expected_cls, expected_kind, kwargs in cases:
            with self.subTest(option_type=option_type.name):
                option = OptionReference(
                    option_type=option_type,
                    card=kwargs.get("card"),
                    zone=kwargs.get("zone"),
                    zone_index=kwargs.get("zone_index"),
                    owner=PlayerSide.SELF,
                    energy_count=kwargs.get("energy_count"),
                    number=kwargs.get("number"),
                    special_condition=kwargs.get("special_condition"),
                )
                selection = SelectPrompt(
                    selection_type=SelectType.MAIN,
                    context=SelectContext.MAIN,
                    min_count=1,
                    max_count=1,
                    options=(option,),
                    effect_context=EffectContext(),
                )
                action = self.factory.from_selection(selection, state=self._build_state())[0]
                self.assertIsInstance(action, expected_cls)
                self.assertEqual(action.kind, expected_kind)

    def test_unknown_option_type_becomes_unknown_action(self) -> None:
        option = OptionReference(option_type=OptionType.UNKNOWN)
        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.MAIN,
            min_count=1,
            max_count=1,
            options=(option,),
            effect_context=EffectContext(),
        )
        action = self.factory.from_selection(selection, state=self._build_state())[0]
        self.assertIsInstance(action, UnknownAction)
        self.assertEqual(action.kind, ActionKind.UNKNOWN)

    def test_missing_card_for_play_raises(self) -> None:
        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.MAIN,
            min_count=1,
            max_count=1,
            options=(OptionReference(option_type=OptionType.PLAY, zone=Zone.HAND, zone_index=0),),
            effect_context=EffectContext(),
        )
        with self.assertRaises(ActionValidationError):
            self.factory.from_selection(selection, state=self._build_state())

    def _build_observation(self) -> Observation:
        raw = {
            "logs": [{"type": 2, "playerIndex": 0}],
            "current": {
                "turn": 3,
                "turnActionCount": 1,
                "yourIndex": 0,
                "firstPlayer": 0,
                "supporterPlayed": False,
                "stadiumPlayed": False,
                "energyAttached": True,
                "retreated": False,
                "result": -1,
                "stadium": [],
                "looking": None,
                "players": [
                    {
                        "active": [{"id": 278, "serial": 1001, "playerIndex": 0, "hp": 30, "maxHp": 30, "appearThisTurn": False, "energies": [5], "energyCards": [{"id": 5, "serial": 3001, "playerIndex": 0}], "tools": [], "preEvolution": []}],
                        "bench": [],
                        "benchMax": 5,
                        "deckCount": 45,
                        "discard": [],
                        "prize": [None, None, None, None, None, None],
                        "handCount": 5,
                        "hand": [{"id": 1, "serial": 2001, "playerIndex": 0}],
                        "poisoned": False,
                        "burned": False,
                        "asleep": False,
                        "paralyzed": False,
                        "confused": False,
                    },
                    {
                        "active": [None],
                        "bench": [],
                        "benchMax": 5,
                        "deckCount": 44,
                        "discard": [],
                        "prize": [None, None, None, None, None, None],
                        "handCount": 4,
                        "hand": None,
                        "poisoned": False,
                        "burned": False,
                        "asleep": False,
                        "paralyzed": False,
                        "confused": False,
                    },
                ],
            },
            "select": {
                "type": 0,
                "context": 0,
                "minCount": 1,
                "maxCount": 1,
                "remainDamageCounter": 0,
                "remainEnergyCost": 0,
                "option": [
                    {"type": 14},
                    {"type": 7, "cardId": 1, "serial": 2001, "playerIndex": 0, "area": 2, "index": 0},
                ],
                "deck": None,
                "contextCard": None,
                "effect": None,
            },
        }
        return self.parser.parse(raw)

    def _build_attack_observation(self) -> Observation:
        raw = {
            "logs": [],
            "current": {
                "turn": 4,
                "turnActionCount": 0,
                "yourIndex": 0,
                "firstPlayer": 0,
                "supporterPlayed": False,
                "stadiumPlayed": False,
                "energyAttached": False,
                "retreated": False,
                "result": -1,
                "stadium": [],
                "looking": None,
                "players": [
                    {
                        "active": [{"id": 21, "serial": 1001, "playerIndex": 0, "hp": 120, "maxHp": 120, "appearThisTurn": False, "energies": [7, 0, 0], "energyCards": [{"id": 7, "serial": 3001, "playerIndex": 0}], "tools": [], "preEvolution": []}],
                        "bench": [],
                        "benchMax": 5,
                        "deckCount": 45,
                        "discard": [],
                        "prize": [None, None, None, None, None, None],
                        "handCount": 2,
                        "hand": [],
                        "poisoned": False,
                        "burned": False,
                        "asleep": False,
                        "paralyzed": False,
                        "confused": False,
                    },
                    {
                        "active": [None],
                        "bench": [],
                        "benchMax": 5,
                        "deckCount": 44,
                        "discard": [],
                        "prize": [None, None, None, None, None, None],
                        "handCount": 4,
                        "hand": None,
                        "poisoned": False,
                        "burned": False,
                        "asleep": False,
                        "paralyzed": False,
                        "confused": False,
                    },
                ],
            },
            "select": {
                "type": 6,
                "context": 35,
                "minCount": 1,
                "maxCount": 1,
                "remainDamageCounter": 0,
                "remainEnergyCost": 0,
                "option": [
                    {"type": 13, "attackId": 101},
                    {"type": 13, "attackId": 102},
                ],
                "deck": None,
                "contextCard": None,
                "effect": None,
            },
        }
        return self.parser.parse(raw)

    def _build_state(self, *, active_card_id: int = 21) -> GameState:
        active = Pokemon(card=self._card(active_card_id, 0), current_hp=120, max_hp=120)
        bench_pokemon = Pokemon(card=self._card(278, 0), current_hp=30, max_hp=30)
        opponent_active = Pokemon(card=self._card(22, 1), current_hp=70, max_hp=70)
        me = Player(player_index=0, side=PlayerSide.SELF, active=active, bench=self._bench(bench_pokemon))
        opponent = Player(player_index=1, side=PlayerSide.OPPONENT, active=opponent_active)
        return GameState(players=(me, opponent))

    def _card(self, card_id: int, player_index: int) -> Card:
        owner = PlayerSide.SELF if player_index == 0 else PlayerSide.OPPONENT
        return Card(metadata=self.card_database.get(card_id), owner=owner, serial=1000 + card_id, player_index=player_index)

    def _bench(self, *pokemon: Pokemon):
        from poketcg.domain import Bench

        return Bench(pokemon=tuple(pokemon), max_size=5)


if __name__ == "__main__":
    unittest.main()
