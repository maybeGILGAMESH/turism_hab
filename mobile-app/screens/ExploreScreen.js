import React, { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, FlatList, Image, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

export default function ExploreScreen({ apiUrl }) {
  const [objects, setObjects] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [route, setRoute] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    fetch(`${apiUrl}/api/objects`).then(response => response.json())
      .then(data => setObjects(data.objects || []))
      .catch(reason => setError(reason.message))
      .finally(() => setLoading(false));
  }, [apiUrl]);

  const filtered = useMemo(() => objects.filter(item =>
    `${item.name} ${item.municipality}`.toLowerCase().includes(query.toLowerCase())), [objects, query]);

  const buildRoute = async () => {
    setError('');
    try {
      const response = await fetch(`${apiUrl}/api/plan-route`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latitude: 48.4800, longitude: 135.0710, limit: 7 }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Не удалось построить маршрут');
      setRoute(data.route || []);
    } catch (reason) { setError(reason.message); }
  };

  if (loading) return <View style={styles.center}><ActivityIndicator color="#0369a1" /></View>;
  return <View style={styles.container}>
    <View style={styles.header}><Text style={styles.title}>Места края</Text><Text style={styles.subtitle}>{objects.length} точек для путешествия</Text></View>
    <TextInput value={query} onChangeText={setQuery} placeholder="Название или район" style={styles.search} />
    <TouchableOpacity style={styles.routeButton} onPress={buildRoute}><Text style={styles.routeText}>🧭 Маршрут по Хабаровску</Text></TouchableOpacity>
    {!!error && <Text style={styles.error}>{error}</Text>}
    {!!route.length && <View style={styles.route}><Text style={styles.routeTitle}>Ближайшие места</Text>{route.map((item, index) => <Text key={item.id}>{index + 1}. {item.name} · {item.distance_from_previous_km} км</Text>)}</View>}
    <FlatList data={filtered} keyExtractor={item => String(item.id)} contentContainerStyle={styles.list}
      renderItem={({ item }) => <View style={styles.card}>
        {item.example_images?.[0] ? <Image source={{ uri: `${apiUrl}${item.example_images[0]}` }} style={styles.image} /> : <View style={styles.placeholder} />}
        <View style={styles.body}><Text style={styles.meta}>{item.municipality} · {item.category}</Text><Text style={styles.name}>{item.name}</Text><Text numberOfLines={3}>{item.description}</Text></View>
      </View>} />
  </View>;
}

const styles = StyleSheet.create({
  container:{flex:1,backgroundColor:'#eef9ff'},center:{flex:1,alignItems:'center',justifyContent:'center'},
  header:{backgroundColor:'#075985',padding:20},title:{fontSize:28,fontWeight:'800',color:'white'},subtitle:{color:'#bae6fd'},
  search:{margin:12,padding:13,borderRadius:14,backgroundColor:'white',borderWidth:1,borderColor:'#bae6fd'},
  routeButton:{marginHorizontal:12,backgroundColor:'#0369a1',borderRadius:14,padding:13},routeText:{color:'white',textAlign:'center',fontWeight:'700'},
  route:{margin:12,padding:14,borderRadius:14,backgroundColor:'#fffaf0'},routeTitle:{fontWeight:'800',marginBottom:6},error:{color:'#b91c1c',margin:12},
  list:{padding:12},card:{backgroundColor:'white',borderRadius:18,overflow:'hidden',marginBottom:14,borderWidth:1,borderColor:'#bae6fd'},
  image:{width:'100%',height:180},placeholder:{height:80,backgroundColor:'#dff5ff'},body:{padding:14},meta:{fontSize:12,color:'#64748b'},name:{fontSize:19,fontWeight:'800',color:'#082f49',marginVertical:5},
});
