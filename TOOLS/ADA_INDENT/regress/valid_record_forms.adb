-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- Every place a record's component list can open: under 'is', after 'with'
-- or 'tagged' ending the line above, 'with record' on either line, with a
-- variant part, with comments among the components, and 'null record'.
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
  X : Integer;
end Records;
