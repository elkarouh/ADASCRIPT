#!/usr/bin/awk -f
function shell_command(cmd) {
    cmd | getline result 
    close(cmd)
    return result
    }

BEGIN {
    in_body=0; in_footer=0; div_processed=0
    # full_path=realpath(ARGV[1])
    full_path=shell_command("realpath \"" ARGV[1] "\"")
    # dir_name=dirname(full_path)
    dir_name=shell_command("dirname \"" full_path "\"")
    # file_name=basename(full_path)
    file_name=shell_command("basename -s .html \"" full_path "\"")
}
/<body.*>/ {  # match start of body tag with possible attributes
    in_body=1
    next
}
/<div title="footer">/ {  # skip footer
    in_footer=1
    next
}
/<\/div>/ && in_footer {
    in_footer=0
    next
}

/<\/body>/ {  # match end of body tag
    exit
}
/<div[^>]/ && in_body && !div_processed {  # add id attribute to first div tag
    $0=gensub(/(<div[^>]*)>/, "\\1 id=\"" file_name "\">","g")
    div_processed=1
}
/<a [^>]*href="test_/ && in_body {
    # Change href links matching criteria to use absolute links
    gsub(/href="test_/, "href=\"" dir_name "/test_", $0)
    # todo use where_tacot or readlink
}
/<img src="/ && in_body {
    # Change image sources to use absolute links
    gsub(/<img src="/, "<img src=\"" dir_name "/", $0)
}
in_body && !in_footer {
    print
}
