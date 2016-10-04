# atop -r ./atop.log -P PRM | awk -f atop-prm-stat.awk

{
  ts=$3
  date=$4
  time=$5
  pid=$8
  rsize=$12
  
  stat[ts]["datetime"] = date " " time
  stat[ts]["rsize"][pid] += rsize
}

END {
  PROCINFO["sorted_in"] = "@ind_num_asc"
  idx = 0
  for (ts in stat) {
    arr[idx++] = ts
  }

  for (i = 1; i < idx; i++) {
    ts = arr[i]
    for (pid in stat[ts]["rsize"]) {
      rsize = stat[ts]["rsize"][pid] / 1024
      if (rsize > 50) {
        procs[pid] += rsize
      }
    }
  }

  PROCINFO["sorted_in"] = "@val_num_desc"
  ostr = " "
  for (pid in procs) {
    ostr = ostr "; " pid
  }
  print ostr

  for (i = 1; i < idx; i++) {
    ts = arr[i]
    ostr = stat[ts]["datetime"]
    for (pid in procs) {
      rsize = stat[ts]["rsize"][pid] / 1024
      ostr = ostr "; " rsize
    }
    print ostr
  }
}
