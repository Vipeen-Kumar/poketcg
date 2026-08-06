"""Thin baseline agent orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import poketcg.rules  # noqa: F401  # Ensure built-in rules register with the shared registry.

from poketcg.actions import ActionBatch, ActionFactory, BaseAction
from poketcg.analysis import GameAnalyzer
from poketcg.cards import CardDatabase
from poketcg.deck import DeckValidator
from poketcg.decision import DecisionContext, DecisionEngine, DecisionOutcome, DecisionTrace, RuleResult
from poketcg.debug import DecisionMetadata, ReplayLogger
from poketcg.domain import ActionSelection, CardType, Deck, Observation, PokemonType, Stage
from poketcg.engine import ObservationParser
from poketcg.rules import FallbackRule

from .config import BaselineAgentConfig
from .interfaces import BaseAgent
from .lifecycle import AgentLifecycle, RawObservation, SubmissionResponse


@dataclass(slots=True)
class BaselineDecisionArtifacts:
    """Typed artifacts created during one baseline-agent decision."""

    observation: Observation
    actions: ActionBatch
    analyzer: GameAnalyzer
    context: DecisionContext


class BaselineAgent(BaseAgent):
    """Thin orchestrator over parsing, analysis, rules, and replay logging."""

    def __init__(
        self,
        *,
        config: BaselineAgentConfig | None = None,
        card_database: CardDatabase,
        observation_parser: ObservationParser,
        action_factory: ActionFactory,
        decision_engine: DecisionEngine,
        replay_logger: ReplayLogger,
    ) -> None:
        self._config = config or BaselineAgentConfig()
        self._card_database = card_database
        self._observation_parser = observation_parser
        self._action_factory = action_factory
        self._decision_engine = decision_engine
        self._replay_logger = replay_logger
        self._fallback_rule = FallbackRule()
        self._deck_validator = DeckValidator(card_database)
        self._game_counter = 0
        self._deck = self._build_deterministic_deck()
        self._deck_validator.validate_or_raise(self._deck)

    @property
    def replay_logger(self) -> ReplayLogger:
        """Return the replay logger used by the agent."""

        return self._replay_logger

    def select_deck(self) -> Deck:
        """Return the deterministic baseline deck."""

        return self._deck

    def act(self, observation: Observation) -> ActionSelection:
        """Select one legal action from a parsed observation."""

        if observation.selection is None:
            if observation.is_terminal:
                self._finish_replay_if_terminal(observation)
            return ActionSelection(selected_option_indices=())

        self._ensure_game_started()
        artifacts = self._build_decision_artifacts(observation)
        selected_action = self._choose_action(artifacts)
        
        # Validate that the selected action is legal before returning
        validated_action = self._validate_action_legality(selected_action, artifacts)
        
        # Trace the decision for debugging
        returned_index = validated_action.action_index
        self._trace_action_decision(observation, artifacts.context.legal_actions, validated_action, returned_index)
        
        self._finish_replay_if_terminal(observation)
        return ActionSelection(selected_option_indices=(returned_index,))

    def handle_observation(self, raw_observation: RawObservation | Observation) -> SubmissionResponse:
        """Handle a raw Kaggle observation or parsed observation end to end."""

        # Debug logging
        import sys
        print(f"[DEBUG] Raw observation keys: {list(raw_observation.keys()) if isinstance(raw_observation, dict) else 'not dict'}", file=sys.stderr)
        if isinstance(raw_observation, dict):
            print(f"[DEBUG] current value: {raw_observation.get('current')}", file=sys.stderr)
            print(f"[DEBUG] select value: {raw_observation.get('select')}", file=sys.stderr)
            print(f"[DEBUG] step value: {raw_observation.get('step')}", file=sys.stderr)
            print(f"[DEBUG] logs value (len): {len(raw_observation.get('logs', [])) if isinstance(raw_observation.get('logs'), list) else 'not list'}", file=sys.stderr)

        if AgentLifecycle.is_deck_selection_payload(raw_observation):
            print("[DEBUG] Detected as deck selection payload", file=sys.stderr)
            self._ensure_game_started()
            print("[DEBUG] Returning actual deck", file=sys.stderr)
            return AgentLifecycle.serialize_deck(self.select_deck())

        print("[DEBUG] Detected as regular observation", file=sys.stderr)
        try:
            parsed = raw_observation if isinstance(raw_observation, Observation) else self._observation_parser.parse(raw_observation)
            return AgentLifecycle.serialize_action_selection(self.act(parsed))
        except Exception as error:
            if isinstance(raw_observation, Mapping) and self._config.safe_raw_fallback:
                fallback = AgentLifecycle.emergency_first_legal_action(raw_observation)
                if fallback is not None:
                    return fallback
            raise RuntimeError("BaselineAgent failed to produce a submission response.") from error

    def __call__(self, raw_observation: RawObservation | Observation) -> SubmissionResponse:
        """Alias for the Kaggle-facing call surface."""

        return self.handle_observation(raw_observation)

    def _build_decision_artifacts(self, observation: Observation) -> BaselineDecisionArtifacts:
        actions = self._action_factory.from_observation(observation)
        analyzer = GameAnalyzer(observation, actions=actions)
        context = DecisionContext(
            analyzer=analyzer,
            legal_actions=actions.actions,
            config=self._config.decision,
            replay_logger=self._replay_logger if self._replay_logger.enabled else None,
            metadata={"agent": self.__class__.__name__},
        )
        return BaselineDecisionArtifacts(observation=observation, actions=actions, analyzer=analyzer, context=context)

    def _choose_action(self, artifacts: BaselineDecisionArtifacts) -> BaseAction:
        try:
            outcome = self._decision_engine.decide(artifacts.context)
            return outcome.action
        except Exception as error:
            fallback_outcome = self._safe_fallback_outcome(artifacts, error)
            return fallback_outcome.action

    def _validate_action_legality(self, selected_action: BaseAction, artifacts: BaselineDecisionArtifacts) -> BaseAction:
        """Validate that the selected action is legal before returning to environment.
        
        If validation fails, returns the first legal action as a safe fallback.
        Performs three-layer validation:
        1. Null check - action exists
        2. Bounds check - action_index is within legal range
        3. Identity check - action object is in the legal_actions tuple
        """
        # Layer 1: Null check
        if selected_action is None:
            # Action is None - use first legal action
            if artifacts.context.legal_actions:
                return artifacts.context.legal_actions[0]
            raise RuntimeError("No legal actions available for validation fallback.")
        
        # Layer 2: Bounds check on action_index
        if not hasattr(selected_action, 'action_index'):
            # Malformed action - use first legal action
            if artifacts.context.legal_actions:
                return artifacts.context.legal_actions[0]
            raise RuntimeError("Selected action has no action_index attribute.")
        
        action_index = selected_action.action_index
        
        if action_index < 0 or action_index >= len(artifacts.context.legal_actions):
            # Invalid index - use first legal action
            if artifacts.context.legal_actions:
                return artifacts.context.legal_actions[0]
            raise RuntimeError(f"Action index {action_index} out of range [0, {len(artifacts.context.legal_actions) - 1}].")
        
        # Layer 3: Identity check - verify action is actually in the tuple
        # This is a critical check because DecisionEngine already performs this, but we verify again
        legal_action_at_index = artifacts.context.legal_actions[action_index]
        
        # First check: object identity (they should be the exact same object)
        if selected_action is not legal_action_at_index:
            # If object identity fails, try equality check in case action was copied
            if not (hasattr(selected_action, 'action_index') and 
                   selected_action.action_index == legal_action_at_index.action_index and
                   type(selected_action) == type(legal_action_at_index)):
                # Action object mismatch - use first legal action (shouldn't happen if DecisionEngine worked correctly)
                if artifacts.context.legal_actions:
                    return artifacts.context.legal_actions[0]
                raise RuntimeError("Selected action object not found in legal actions after identity check.")
        
        # Action is valid
        return selected_action

    def _safe_fallback_outcome(self, artifacts: BaselineDecisionArtifacts, error: Exception) -> DecisionOutcome:
        try:
            fallback_result = self._fallback_rule.evaluate(artifacts.context)
            if fallback_result.passed and fallback_result.selected_action is not None:
                trace = self._build_emergency_trace(
                    primary_reason=str(error),
                    selected_result=fallback_result,
                )
                self._log_emergency_trace(artifacts, fallback_result.selected_action, trace)
                return DecisionOutcome(action=fallback_result.selected_action, trace=trace)
        except Exception as fallback_error:
            fallback_note = f"{error!r}; fallback rule failed with {fallback_error!r}"
        else:
            fallback_note = str(error)

        if artifacts.context.legal_actions:
            action = artifacts.context.legal_actions[0]
            first_legal_result = RuleResult(
                rule_name="FirstLegalActionFallback",
                passed=True,
                selected_action=action,
                reason="Selected the first legal action after decision-engine failure.",
                priority=-10_000,
                metadata={"emergency": True},
                execution_time=0.0,
            )
            trace = self._build_emergency_trace(primary_reason=fallback_note, selected_result=first_legal_result)
            self._log_emergency_trace(artifacts, action, trace)
            return DecisionOutcome(action=action, trace=trace)

        raise RuntimeError("BaselineAgent encountered a decision failure with no legal fallback action available.") from error

    def _build_emergency_trace(self, *, primary_reason: str, selected_result: RuleResult) -> DecisionTrace:
        engine_failure = RuleResult(
            rule_name="DecisionEngineError",
            passed=False,
            selected_action=None,
            reason=primary_reason,
            priority=0,
            metadata={"emergency": True},
            execution_time=0.0,
        )
        return DecisionTrace(
            rule_results=(engine_failure, selected_result),
            selected_action=selected_result.selected_action,
            selected_rule_name=selected_result.rule_name,
            fallback_used=True,
            fallback_reason=selected_result.reason,
            metadata={"agent": self.__class__.__name__, "emergency": True},
        )

    def _log_emergency_trace(self, artifacts: BaselineDecisionArtifacts, action: BaseAction, trace: DecisionTrace) -> None:
        if not self._replay_logger.enabled:
            return
        self._replay_logger.log_turn(
            artifacts.observation,
            chosen_action=action,
            decision_metadata=DecisionMetadata(
                rule_name=trace.selected_rule_name,
                reason=trace.selected_result.reason if trace.selected_result is not None else "Emergency fallback used.",
                notes=trace.rule_results[0].reason,
            ),
            decision_trace=trace,
            analyzer=artifacts.analyzer,
        )

    def _ensure_game_started(self) -> None:
        if not self._replay_logger.enabled:
            return
        session = self._replay_logger.session
        if session is not None and session.status == "in_progress":
            return
        self._game_counter += 1
        game_id = f"{self._config.game_id_prefix}_{self._game_counter:03d}"
        
        # Reset trace collector for new game
        from poketcg.debug.action_trace import reset_trace_collector
        reset_trace_collector()
        
        self._replay_logger.start_game(
            game_id,
            metadata={"deck_name": self._deck.name, "deck_size": len(self._deck.card_ids)},
        )

    def _trace_action_decision(
        self,
        observation: Observation,
        legal_actions: tuple[BaseAction, ...],
        chosen_action: BaseAction | None,
        returned_index: int,
    ) -> None:
        """Trace the action decision for debugging purposes."""
        from poketcg.debug.action_trace import get_trace_collector

        trace_collector = get_trace_collector()
        
        # Determine validation status
        validation_passed = True
        validation_error = None
        
        if returned_index is not None and observation.selection is not None:
            legal_option_count = len(observation.selection.options) if observation.selection.options else 0
            if returned_index < 0 or returned_index >= legal_option_count:
                validation_passed = False
                validation_error = f"Index {returned_index} out of bounds [0, {legal_option_count - 1}]"
            elif chosen_action is not None:
                # Additional check: is the chosen action actually in the legal_actions tuple?
                if chosen_action not in legal_actions:
                    validation_passed = False
                    validation_error = f"Chosen action object not in legal_actions tuple (length={len(legal_actions)})"
        
        trace_collector.trace_decision(
            observation=observation,
            legal_actions=legal_actions,
            chosen_action=chosen_action,
            returned_integer=returned_index,
            validation_passed=validation_passed,
            validation_error=validation_error,
            decision_error=None,
        )

    def _finish_replay_if_terminal(self, observation: Observation) -> None:
        if not self._replay_logger.enabled or not observation.is_terminal:
            return
        
        # Print action trace before finishing replay
        from poketcg.debug.action_trace import get_trace_collector

        trace_collector = get_trace_collector()
        trace_output = trace_collector.log_turn_summary()
        print(trace_output)

        # Export trace as JSON if replay is enabled
        session = self._replay_logger.session
        if session is not None:
            import json
            from pathlib import Path

            trace_json_path = Path("outputs/replays") / f"trace_{session.game_id}.json"
            trace_json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(trace_json_path, "w") as f:
                f.write(trace_collector.to_json())

        if session is None or session.status != "in_progress":
            return
        result = None if observation.result is None else observation.result.name
        self._replay_logger.finish(metadata={"result": result})

    def _build_deterministic_deck(self) -> Deck:
        basics = [
            card
            for card in self._card_database.by_stage(Stage.BASIC)
            if card.is_pokemon() and card.attacks and card.pokemon_type not in {None, PokemonType.UNKNOWN}
        ]
        if len(basics) < 5:
            raise ValueError("Card database does not contain enough Basic Pok\u00e9mon to build the baseline deck.")

        chosen_basics = basics[:5]
        trainer_pool = [
            card
            for card in self._card_database.all_cards()
            if card.card_type in {CardType.ITEM, CardType.SUPPORTER, CardType.STADIUM, CardType.TOOL}
            and not card.is_ace_spec()
        ]
        if len(trainer_pool) < 5:
            raise ValueError("Card database does not contain enough Trainer cards to build the baseline deck.")

        chosen_trainers = trainer_pool[:5]
        deck_ids: list[int] = []
        for card in chosen_basics:
            deck_ids.extend([card.card_id] * 4)
        for card in chosen_trainers:
            deck_ids.extend([card.card_id] * 4)

        required_energy_cards = self._energy_cards_for_basics(chosen_basics, total_energy_cards=20)
        deck_ids.extend(required_energy_cards)

        if len(deck_ids) != 60:
            raise ValueError(f"Baseline deck construction produced {len(deck_ids)} cards instead of 60.")
        return Deck(card_ids=tuple(deck_ids), name=self._config.deck_name)

    def _energy_cards_for_basics(self, basics: list, *, total_energy_cards: int) -> list[int]:
        chosen_types = [card.pokemon_type for card in basics if card.pokemon_type not in {None, PokemonType.COLORLESS}]
        unique_types = tuple(dict.fromkeys(chosen_types))
        if not unique_types:
            raise ValueError("Baseline deck construction requires at least one typed Basic Pok\u00e9mon.")

        energy_by_type: dict[PokemonType, int] = {}
        base_count, remainder = divmod(total_energy_cards, len(unique_types))
        for index, pokemon_type in enumerate(unique_types):
            energy_by_type[pokemon_type] = base_count + (1 if index < remainder else 0)

        basic_energy_cards = list(self._card_database.by_type(CardType.BASIC_ENERGY))
        energy_lookup = {card.pokemon_type: card for card in basic_energy_cards if card.pokemon_type is not None}
        deck_ids: list[int] = []
        for pokemon_type in unique_types:
            energy_card = energy_lookup.get(pokemon_type)
            if energy_card is None:
                raise ValueError(f"No basic energy card found for Pok\u00e9mon type {pokemon_type.name}.")
            deck_ids.extend([energy_card.card_id] * energy_by_type[pokemon_type])
        return deck_ids
