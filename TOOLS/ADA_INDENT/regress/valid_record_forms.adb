-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- Every place a record's component list can open: under 'is', after 'with'
-- or 'tagged' ending the line above, 'with record' on either line, with a
-- variant part, with comments among the components, and 'null record';
-- and a discriminant part ending in 'is record' on either line.
package body Records is
  type Obj_T is new Base_Tree.Tree_Obj_T with
    record
      -- It represents a distance_range at which a specified level is requested.
      Distance_Range : Curtain.Distance_Pair.T;
      -- Horizontal range covered by the Requested Flight Level
      Level : Level_T;
    end record;
  type A is new Base with
    record
      X : Integer;
      case K is
        when 1 =>
          Y : Integer;
        when others =>
          null;
      end case;
    end record;
  type B is tagged
    record
      Z : Integer;
    end record;
  type C is new Base
    with record
      W : Integer;
    end record;
  type D is new Base with record
    V : Integer;
  end record;
  type E is
    record
      U : Integer;
    end record;
  type F is new Base with null record;
  type RL_And_Aerodrome_Info_T
    (Aerodrome_Implication : Aerodrome_Implication_T := Found_No_Elements_Yet) is record
    case Aerodrome_Implication is
      when Found_No_Elements_Yet =>
        null;
        -- This is the initial value, and never the final value.
      when Found_All_Elements_Implying_Aerodrome =>
        Aerodrome     : Env_Aerodrome.T;
        Terminal_Type : Env_Flow_Expression.Terminal_Location.T;
      when Non_Optimizable_T =>
        Add_RL : Boolean;
        -- Indicates that the reference location contains constructs implying a sequence.
    end case;
  end record;
  type A (D : Integer) is record
    X : Integer;
  end record;
  type B
    (D : Integer)
  is record
    X : Integer;
  end record;
  type C (D : Integer) is new Base with
    record
      X : Integer;
    end record;
  type E is abstract tagged
    limited record
      X : Integer;
    end record;
  X : Integer;
end Records;
