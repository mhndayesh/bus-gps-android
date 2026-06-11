package com.busgps.android.ui.superadmin

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.busgps.android.databinding.ItemBusSuperBinding
import com.busgps.android.model.Bus

class SuperBusAdapter(
    private val buses: List<Bus>,
    private val onAssignDriver: (String) -> Unit,
    private val onDelete: (String) -> Unit
) : RecyclerView.Adapter<SuperBusAdapter.VH>() {

    inner class VH(val binding: ItemBusSuperBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemBusSuperBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = buses.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val bus = buses[position]
        holder.binding.apply {
            tvPlate.text = bus.plate
            tvBusId.text = "Bus #${bus.id}"
            btnAssignDriver.setOnClickListener { onAssignDriver(bus.id) }
            btnDelete.setOnClickListener { onDelete(bus.id) }
        }
    }
}
