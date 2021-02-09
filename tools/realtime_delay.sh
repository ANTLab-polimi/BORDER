HOSTNAME="localhost"
TOPIC="test"
QOS=2

echo "Subscribed to $HOSTNAME on topic \`$TOPIC\` (QoS: $QOS)"

mosquitto_sub -h $HOSTNAME -t $TOPIC -q $QOS -v | gxargs -d '\n' -L1 bash -c 'gdate "+%s%3N ---- $0"' |
  while IFS= read -r line
  do
	  array=($line)
	  #echo "$line"
	  sent="${array[3]}"
	  #echo $sent
	  now=$(gdate "+%s%3N")
	  diff=$((now - sent))
	  echo "${diff}"
  done

#mosquitto_pub -h 172.17.0.2 -q 2 -t test -m $(date +"%Y-%m-%d_%T.%3N") -d | xargs -d$'\n' -L1 bash -c 'date "+%Y-%m-%d %T.%3N ---- $0"'; done