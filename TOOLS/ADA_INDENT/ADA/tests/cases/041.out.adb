function F return Boolean is
  (case Y is
     when A | B =>
       First_Cond
         -- head note
         or else Second_Cond
         -- middle note
         or else Third_Cond,
     when others => False);
