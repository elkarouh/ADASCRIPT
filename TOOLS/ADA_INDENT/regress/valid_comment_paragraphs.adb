-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- A comment belongs to the line before it, unless a blank line precedes it:
-- then it belongs to the line after it and takes that line's column. Except
-- before a line that carries no meaning of its own ('end ...', 'begin', a lone
-- ')'): there the comment stays with the block it ends.
package body Paragraphs is

  function Image (Extended : Extended_T; Kind : Kind_T) return String is
  begin
    case Kind is
      when Aircraft_Operators =>
        if With_Details then
          return Operators_Image (Extended);
        end if;

      -- Below: currently no specific processing when With_Details is true.
      when For_FPL_Origin_Unit =>
        return "FPL Origin Unit Id " & Unit_Image (Extended);

      -- Everything else has no image.
      when others =>
        null;
    end case;
    if A then
      X := 1;

    -- The usual case.
    elsif B then
      X := 2;

    -- Nothing matched.
    else
      X := 3;
    end if;
    return "";

  -- Handlers: anything unexpected is reported as unknown.
  exception
    when others =>
      return "unknown";
  end Image;

  procedure Q is
    Count : Natural := 0;

    -- A note on the declarations, kept at their column before 'begin'.
  begin
    Step_One;

    -- A note on the next step, at the statement's column anyway.
    Step_Two;

    -- A trailing note on the body, kept at its column before 'end'.
  end Q;

  procedure Call is
  begin
    Put (Item  => 1,
         Width => 2

         -- a note on the arguments, kept before the lone ')'
         );
  end Call;

end Paragraphs;
