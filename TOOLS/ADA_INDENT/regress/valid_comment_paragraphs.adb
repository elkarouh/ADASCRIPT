-- Regression fixture for ada_indent (fixpoint, also from flattened input).
-- A comment paragraph (after a blank line, straight before its code line)
-- introduces that line: before a new alternative or branch it takes that
-- line's column. Before 'end' or a plain statement it keeps the block's.
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
  begin
    Step_One;

    -- A note on the next step, at the statement's column anyway.
    Step_Two;

    -- A trailing note on the body, kept at its column before 'end'.
  end Q;

end Paragraphs;
