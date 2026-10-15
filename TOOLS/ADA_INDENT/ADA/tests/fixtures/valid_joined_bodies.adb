-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- Layouts found by metamorphic_check.py: a body started beside the keyword
-- that opens it, and a 'then' moved to its own line after a nested 'if'.
package body Joined is

  procedure Scan is
  begin
    for I in 1 .. Length (List) loop Item := Value (List, I);
      exit when Item = null;
    end loop;
    while More loop Next;
      Count := Count + 1;
    end loop;
  end Scan;

  function Origin return String is
  begin
    case Compare (Entry_Time, Start_Time) is
      when Order.Smaller => return "Live";
      when Order.Equal => if Controlled then return "Simul";
        else
          return "Live";
        end if;
      when others => return "Unknown";
    end case;
  end Origin;

  procedure Nested is
  begin
    if A then if B
    then
        null;
      end if;
    end if;
  end Nested;

end Joined;
