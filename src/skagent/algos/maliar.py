import numpy as np
import skagent.ann as ann
import skagent.model as model
from skagent.simulation.monte_carlo import draw_shocks
import torch

"""
Tools for the implementation of the Maliar, Maliar, and Winant (JME '21) method.

This method relies on a simpler problem representation than that elaborated
by the skagent Block system.

"""


def create_transition_function(block, state_syms):
    """
    block
    state_syms : list of string
        A list of symbols for 'state variables at time t', aka arrival states.
        # TODO: state variables should be derived from the block analysis.
    """

    def transition_function(states_t, shocks_t, controls_t, parameters):
        vals = parameters | states_t | shocks_t | controls_t
        post = block.transition(vals, {}, fix=list(controls_t.keys()))

        return {sym: post[sym] for sym in state_syms}

    return transition_function


def create_decision_function(block, decision_rules):
    """
    block
    decision_rules
    """

    def decision_function(states_t, shocks_t, parameters):
        if parameters is None:
            parameters = {}
        vals = parameters | states_t | shocks_t
        post = block.transition(vals, decision_rules)

        return {sym: post[sym] for sym in decision_rules}

    return decision_function


def create_reward_function(block, agent=None):
    """
    block
    agent : optional, str
    """

    def reward_function(states_t, shocks_t, controls_t, parameters):
        vals_t = parameters | states_t | shocks_t | controls_t
        post = block.transition(vals_t, {}, fix=list(controls_t.keys()))
        return {
            sym: post[sym]
            for sym in block.reward
            if agent is None or block.reward[sym] == agent
        }

    return reward_function


def estimate_discounted_lifetime_reward(
    block,
    discount_factor,
    dr,
    states_0,
    big_t,
    shocks_by_t=None,
    parameters={},
    agent=None,
):
    """
    block
    discount_factor - can be a number or a function of state variables
    dr - decision rules (dict of functions), or optionally a decision function (a function that returns the decisions)
    states_0 - dict - initial states, symbols : values (scalars work; TODO: do vectors work here?)
    shocks_by_t - dict - sym : big_t vector of shock values at each time period
    big_t - integer. Number of time steps to simulate forward
    parameters - optional - calibration parameters
    agent - optional - name of reference agent for rewards
    """
    states_t = states_0
    total_discounted_reward = 0

    tf = create_transition_function(block, list(states_0.keys()))

    if callable(dr):
        # assume a full decision function has been passed in
        df = dr
    else:
        # create a decision function from the decision rule
        df = create_decision_function(block, dr)

    rf = create_reward_function(block, agent)

    # this assumes only one reward is given.
    # can be generalized in the future.
    rsym = list(
        {sym for sym in block.reward if agent is None or block.reward[sym] == agent}
    )[0]

    if callable(discount_factor):
        raise Exception(
            "Currently only numerical, not state-dependent, discount factors are supported."
        )

    for t in range(big_t):
        # TODO
        if shocks_by_t is not None:
            shocks_t = {sym: shocks_by_t[sym][t] for sym in shocks_by_t}
        else:
            shocks_t = {}

        controls_t = df(states_t, shocks_t, parameters)
        reward_t = rf(states_t, shocks_t, controls_t, parameters)

        # assumes torch
        if isinstance(reward_t[rsym], torch.Tensor) and torch.any(
            torch.isnan(reward_t[rsym])
        ):
            raise Exception(f"Calculated reward {[rsym]} is NaN: {reward_t}")
        if isinstance(reward_t[rsym], np.ndarray) and np.any(np.isnan(reward_t[rsym])):
            raise Exception(f"Calculated reward {[rsym]} is NaN: {reward_t}")

        total_discounted_reward += reward_t[rsym] * discount_factor**t

        # t + 1
        states_t = tf(states_t, shocks_t, controls_t, parameters)

    return total_discounted_reward


def get_estimated_discounted_lifetime_reward_loss(
    state_variables, block, discount_factor, big_t, parameters
):
    # TODO: Should be able to get 'state variables' from block
    # Maybe with ZP's analysis modules

    # convoluted
    # TODO: codify this encoding and decoding of the grid into a separate object
    # It is specifically the EDLR loss function that requires big_t of the shocks.
    # other AiO loss functions use 2 copies of the shocks only.
    shock_vars = block.get_shocks()
    big_t_shock_syms = sum(
        [[f"{sym}_{t}" for sym in list(shock_vars.keys())] for t in range(big_t)], []
    )

    # will work for big_t = 1 only.
    given_syms = state_variables + big_t_shock_syms

    def estimated_discounted_lifetime_reward_loss(df, input_vector):
        ## includes the values of state_0 variables, and shocks.
        given_vals = dict(zip(given_syms, input_vector))

        shock_vals = {sym: given_vals[sym] for sym in big_t_shock_syms}
        shocks_by_t = {
            sym: torch.stack([shock_vals[f"{sym}_{t}"] for t in range(big_t)])
            for sym in shock_vars
        }

        ####block, discount_factor, dr, states_0, big_t, parameters={}, agent=None
        edlr = estimate_discounted_lifetime_reward(
            block,
            discount_factor,
            df,
            {sym: given_vals[sym] for sym in state_variables},
            big_t,
            parameters=parameters,
            agent=None,  ## TODO: Pass through the agent?
            shocks_by_t=shocks_by_t,
            ## Handle multiple decision rules?
        )
        return -edlr

    return estimated_discounted_lifetime_reward_loss


def generate_givens_from_state_config(state_config, block, shock_copies: int):
    """
    Generates omega_i values of the MMW JME '21 method.

    state_config : a grid configuration for the starting state values (exogenous and endogenous)
    block: block information (used to get the shock names)
    shock_copies : int - number of copies of the shocks to be included.
    """

    # TODO: create a grid with the states, and shock_copies copies of the shocks.
    #       - how are these values to be set?
    #       - by sampling?
    raise Exception("generate_givens_from_states not implemented")

    pass


def generate_givens_from_states(states, block, shock_copies: int):
    """
    Generates omega_i values of the MMW JME '21 method.

    states : a grid of starting state values (exogenous and endogenous)
    block: block information (used to get the shock names)
    shock_copies : int - number of copies of the shocks to be included.
    """

    # TODO: create a grid with the states, and shock_copies copies of the shocks.
    #       - how are these values to be set?
    #       - by sampling?
    raise Exception("generate_givens_from_states not implemented")

    pass


def simulate_forward(
    states_t,
    block: model.Block,
    decision_function: callable,
    parameters,
    big_t,
    state_syms,
):
    tf = create_transition_function(block, state_syms)

    for t in range(big_t):
        # TODO: make sure block shocks are 'constructed'
        # TODO: allow option for 'structured' draws, e.g. from exact discretization.
        shocks_t = draw_shocks(block.shocks)
        decision_function(states_t, shocks_t, parameters)

        states_t_plus_1 = tf(...)
        states_t = states_t_plus_1

    return states_t_plus_1


def maliar_training_loop(
    block,
    loss_function,
    states_0_n,
    parameters,
    shock_copies=2,
    max_iterations=None,
    random_seed=None,
):
    """
    block - a model definition
    loss_function : callable((df, input_vector) -> loss vector
    states_0_n : a panel of starting states
    parameters : dict : given parameters for the model

    shock_copies: int : number of copies of shocks to include in the training set omega
                        must match expected number of shock copies in the loss function
                        TODO: make this better, less ad hoc

    loss_function is the "empirical risk Xi^n" in MMW JME'21.
    """

    # Step 1. Initialize the algorithm:

    # i). construct theoretical risk Xi(θ ) = Eω [ξ (ω; θ )] (lifetime reward, Euler/Bellmanequations);
    # ii). deﬁne empirical risk Xi^n (θ ) = 1n ni=1 ξ (ωi ; θ );
    loss_function  # This is provided as an argument.

    # iii). deﬁne a topology of neural network ϕ (·, θ );
    # iv). ﬁx initial vector of the coeﬃcients θ .

    if random_seed is not None:
        torch.manual_seed(random_seed)

    bpn = ann.BlockPolicyNet(block, width=16)

    states = states_0_n  # V) Create initial panel of agents/starting states.

    # Step 2. Train the machine, i.e., ﬁnd θ that minimizes theempirical risk Xi^n (θ ):
    for i in range(100):
        # i). simulate the model to produce data {ωi }ni=1 by using the decision rule ϕ (·, θ );
        givens = generate_givens_from_states(states_0_n, block, shock_copies)

        # ii). construct the gradient ∇ Xi^n (θ ) = 1n ni=1 ∇ ξ (ωi ; θ );
        # iii). update the coeﬃcients θ_hat = θ − λk ∇ Xi^n (θ ) and go to step 2.i);
        # TODO how many epochs? What Adam scale? Passing through variables
        ann.train_block_policy_nn(bpn, givens, loss_function, epochs=250)

        # i/iv). simulate the model to produce data {ωi }ni=1 by using the decision rule ϕ (·, θ );
        # TODO using SHOCKS (maybe new shocks), and ANN.DF, _transition the agents forward...
        states = simulate_forward(
            states, block, bpn.get_decision_function(), parameters
        )

        # End Step 2 if the convergence criterion || θ_hat − θ ||  < ε is satisﬁed.
        # TODO: test for difference.. how? This effects the FOR (/while) loop above.

    # Step 3. Assess the accuracy of constructed approximation ϕ (·, θ ) on a new sample.
    return ann, states
